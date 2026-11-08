"""Durable batch plans, generation checkpoints and leased jobs."""
import json
import logging
from uuid import uuid4
from .agent_evolution import connect
logger=logging.getLogger(__name__)


class BatchStore:
    def plan(self, owner, plan_id):
        with connect() as conn:
            return conn.execute('SELECT * FROM a12_batch_plan WHERE id=%s AND user_id=%s', (plan_id, owner)).fetchone()

    def save_plan(self, owner, payload, *, plan_id=None, revision=None, session_id=None):
        encoded = json.dumps(payload, ensure_ascii=False)
        with connect() as conn:
            if plan_id:
                row = conn.execute("""UPDATE a12_batch_plan SET payload=%s::jsonb,revision=revision+1,updated_at=NOW()
                    WHERE id=%s AND user_id=%s AND revision=%s AND status='draft' RETURNING *""",
                    (encoded, plan_id, owner, revision)).fetchone()
                if not row:
                    raise ValueError('计划已更新或已确认，请刷新后重试')
                return row
            conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('batch-plan:'+owner,))
            if conn.execute("SELECT COUNT(*) AS n FROM a12_batch_plan WHERE user_id=%s AND created_at>NOW()-INTERVAL '24 hours'",(owner,)).fetchone()['n']>=30:
                raise ValueError('今天批量计划较多，请复用已有计划或稍后再试')
            return conn.execute("""INSERT INTO a12_batch_plan(id,user_id,session_id,payload)
                VALUES (%s,%s,%s,%s::jsonb) RETURNING *""", (uuid4().hex, owner, session_id, encoded)).fetchone()

    def list_plans(self, owner, session_id=None):
        with connect() as conn:
            rows = conn.execute("""SELECT * FROM a12_batch_plan WHERE user_id=%s AND (%s::text IS NULL OR session_id=%s)
                ORDER BY updated_at DESC LIMIT 20""", (owner, session_id, session_id)).fetchall()
        return rows

    def confirm(self, owner, plan_id, revision, selected, theme, accept_suggested, enable_rag=None):
        with connect() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', ('batch-confirm:' + owner,))
            plan = conn.execute('SELECT * FROM a12_batch_plan WHERE id=%s AND user_id=%s FOR UPDATE', (plan_id, owner)).fetchone()
            if not plan:
                raise ValueError('计划不存在')
            if plan['status'] == 'confirmed':
                return plan_id
            if plan['revision'] != revision:
                raise ValueError('计划已变化，请刷新后再确认')
            payload = plan['payload']
            if payload.get('needs_input'):
                raise ValueError('请先补充目录或明确允许使用建议目录')
            if payload.get('basis') == 'suggested' and not accept_suggested:
                raise ValueError('请先确认此计划是 AI 建议目录，不是已核验的教材目录')
            items = [item for item in payload['items'] if item['id'] in set(selected)]
            if not items or len(items) != len(set(selected)) or len(items) > 24:
                raise ValueError('请选择 1–24 个有效章节')
            if sum(item['max_pages'] for item in items) > 240:
                raise ValueError('单批最多 240 页，请缩小范围或分批生成')
            active = conn.execute("""SELECT COUNT(*) AS count FROM a12_batch_job WHERE user_id=%s
                AND status IN ('queued','running')""", (owner,)).fetchone()['count']
            if active:
                raise ValueError('当前还有批量生成任务，请先完成或取消后再提交')
            conn.execute("INSERT INTO a12_batch_job(id,user_id,title,theme) VALUES (%s,%s,%s,%s)", (plan_id, owner, payload['title'], theme))
            for order, item in enumerate(items, 1):
                item = {**item,'subject':payload.get('subject',''),'grade':payload.get('grade',''),
                        'enable_rag': bool(payload.get('enable_rag')) if enable_rag is None else enable_rag,
                        'reasoning_effort':payload.get('reasoning_effort','low'),
                        'requirements':payload.get('requirements','')+'\n教材版本：'+payload.get('textbook_version','')}
                conn.execute("""INSERT INTO a12_batch_item(id,batch_id,user_id,item_order,title,payload)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
                    (item['id'], plan_id, owner, order, item['title'], json.dumps(item, ensure_ascii=False)))
            conn.execute("UPDATE a12_batch_plan SET status='confirmed',updated_at=NOW() WHERE id=%s", (plan_id,))
        return plan_id

    def get(self, owner, batch_id):
        with connect() as conn:
            batch = conn.execute('SELECT * FROM a12_batch_job WHERE id=%s AND user_id=%s', (batch_id, owner)).fetchone()
            if not batch:
                return None
            batch['items'] = conn.execute("""SELECT id,item_order,title,status,stage,progress,attempts,error,project_id,
                updated_at FROM a12_batch_item WHERE batch_id=%s ORDER BY item_order""", (batch_id,)).fetchall()
        batch['progress'] = round(sum(item['progress'] for item in batch['items']) / max(1, len(batch['items'])))
        return batch

    def list(self, owner):
        with connect() as conn:
            ids = conn.execute('SELECT id FROM a12_batch_job WHERE user_id=%s ORDER BY created_at DESC LIMIT 30', (owner,)).fetchall()
        return [self.get(owner, row['id']) for row in ids]

    def item(self, owner, batch_id, item_id):
        with connect() as conn:
            return conn.execute('SELECT * FROM a12_batch_item WHERE id=%s AND batch_id=%s AND user_id=%s', (item_id, batch_id, owner)).fetchone()

    def claim(self):
        with connect() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(120260905)')
            recovered=conn.execute("""UPDATE a12_batch_item SET status=CASE WHEN attempts<3 THEN 'queued' ELSE 'failed' END,
                error='服务中断，等待恢复',lease_id=NULL WHERE status='running' AND updated_at<NOW()-INTERVAL '2 minutes' RETURNING batch_id""").fetchall()
            for row in recovered:self._aggregate(conn,row['batch_id'])
            count = conn.execute("SELECT COUNT(*) AS count FROM a12_batch_item WHERE status='running'").fetchone()['count']
            if count >= 2:
                return None
            item = conn.execute("""SELECT i.*,b.theme,b.title AS course_title FROM a12_batch_item i JOIN a12_batch_job b ON b.id=i.batch_id
                WHERE i.status='queued' AND i.next_attempt_at<=NOW() AND i.attempts<3 AND b.status IN ('queued','running')
                AND NOT EXISTS(SELECT 1 FROM a12_batch_item active WHERE active.user_id=i.user_id AND active.status='running')
                ORDER BY i.created_at,i.item_order FOR UPDATE OF i SKIP LOCKED LIMIT 1""").fetchone()
            if not item:
                return None
            lease = uuid4().hex
            conn.execute("UPDATE a12_batch_item SET status='running',stage='准备生成',attempts=attempts+1,lease_id=%s,updated_at=NOW() WHERE id=%s", (lease, item['id']))
            conn.execute("UPDATE a12_batch_job SET status='running',updated_at=NOW() WHERE id=%s", (item['batch_id'],))
            item['lease_id'] = lease
            return item

    def update(self, item, *, stage=None, progress=None, output=None, status=None, error=''):
        with connect() as conn:
            row = conn.execute("""UPDATE a12_batch_item SET stage=COALESCE(%s,stage),progress=COALESCE(%s,progress),
                output=COALESCE(%s::jsonb,output),status=COALESCE(%s,status),error=%s,updated_at=NOW()
                WHERE id=%s AND status='running' AND lease_id=%s RETURNING id""",
                (stage, progress, json.dumps(output, ensure_ascii=False) if output is not None else None, status, error[:500], item['id'], item['lease_id'])).fetchone()
            if not row:
                import asyncio
                raise asyncio.CancelledError('任务已取消或处理权已移交')
            if status:
                self._aggregate(conn, item['batch_id'])
        if stage is not None or status is not None:
            logger.info('批量任务阶段 batch=%s item=%s stage=%s status=%s progress=%s',
                item['batch_id'],item['id'],stage or '-',status or 'running',progress)

    def defer(self, item):
        with connect() as conn:
            conn.execute("""UPDATE a12_batch_item SET status='queued',attempts=GREATEST(0,attempts-1),
                stage='等待生成配额',next_attempt_at=NOW()+INTERVAL '15 seconds',updated_at=NOW()
                WHERE id=%s AND status='running' AND lease_id=%s""", (item['id'], item['lease_id']))

    def saved(self, owner, batch_id, item_id, project_id):
        with connect() as conn:
            changed = conn.execute("""UPDATE a12_batch_item SET project_id=%s,status='completed',stage='已保存到个人项目',progress=100,
                updated_at=NOW() WHERE id=%s AND batch_id=%s AND user_id=%s AND status IN ('ready','completed')
                AND (project_id IS NULL OR project_id=%s)""", (project_id, item_id, batch_id, owner, project_id)).rowcount
            if not changed:
                raise ValueError('当前产物尚未生成或项目映射不匹配')
            self._aggregate(conn, batch_id)

    def retry(self, owner, batch_id, item_id):
        with connect() as conn:
            batch = conn.execute('SELECT * FROM a12_batch_job WHERE id=%s AND user_id=%s FOR UPDATE', (batch_id, owner)).fetchone()
            if not batch or batch['zip_status'] in ('queued','running'):
                raise ValueError('批次不存在或正在打包，请稍后重试')
            changed = conn.execute("""UPDATE a12_batch_item SET status='queued',error='',stage='等待重试',next_attempt_at=NOW(),updated_at=NOW()
                WHERE id=%s AND batch_id=%s AND user_id=%s AND status='failed' AND attempts<3""", (item_id,batch_id,owner)).rowcount
            if not changed:
                raise ValueError('仅可重试失败项，每项最多 3 次实际执行')
            conn.execute("UPDATE a12_batch_job SET status='queued',zip_status='idle',updated_at=NOW() WHERE id=%s", (batch_id,))

    def cancel(self, owner, batch_id):
        with connect() as conn:
            conn.execute("UPDATE a12_batch_item SET status='cancelled',stage='已取消',updated_at=NOW() WHERE batch_id=%s AND user_id=%s AND status IN ('queued','running')", (batch_id, owner))
            conn.execute("UPDATE a12_batch_job SET status='cancelled',zip_status=CASE WHEN zip_status IN ('queued','running') THEN 'cancelled' ELSE zip_status END WHERE id=%s AND user_id=%s", (batch_id, owner))

    @staticmethod
    def _aggregate(conn, batch_id):
        counts = conn.execute("""SELECT COUNT(*) FILTER(WHERE status IN ('queued','running')) AS active,
            COUNT(*) FILTER(WHERE status='failed') AS failed,COUNT(*) FILTER(WHERE status='ready') AS ready,
            COUNT(*) FILTER(WHERE status='cancelled') AS cancelled FROM a12_batch_item WHERE batch_id=%s""", (batch_id,)).fetchone()
        status = 'running' if counts['active'] else 'partial_failed' if counts['failed'] else 'ready' if counts['ready'] else 'cancelled' if counts['cancelled'] else 'completed'
        conn.execute('UPDATE a12_batch_job SET status=%s,updated_at=NOW() WHERE id=%s', (status,batch_id))


batch_store = BatchStore()
