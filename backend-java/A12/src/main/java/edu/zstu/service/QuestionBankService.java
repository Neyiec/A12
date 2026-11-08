package edu.zstu.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import jakarta.annotation.PostConstruct;
import java.math.BigDecimal;
import java.util.*;

/** 题库是业务数据：公开审核、所有权和试卷快照均由 Java 管理，不转发 AI 请求。 */
@Service
public class QuestionBankService {
    private final JdbcTemplate db;
    private final ObjectMapper json;
    public QuestionBankService(JdbcTemplate db, ObjectMapper json) { this.db=db; this.json=json; }
    @PostConstruct public void initialize() {
        new ResourceDatabasePopulator(new ClassPathResource("db/question_bank.sql")).execute(Objects.requireNonNull(db.getDataSource()));
    }
    private String text(Map<String,Object> body,String key,int max,boolean required) {
        String value=Objects.toString(body.get(key),"").trim();
        if ((required && value.isEmpty()) || value.codePointCount(0,value.length())>max) throw new IllegalArgumentException(key+" 为空或超过长度限制（"+max+"）");
        return value;
    }
    private String encode(Object value) { try {return json.writeValueAsString(value);}catch(Exception e){throw new IllegalArgumentException("内容无法保存");} }
    private int integer(Map<String,Object> body,String key,int defaultValue,int min,int max) {
        Object raw=body.getOrDefault(key,defaultValue);
        try { int value=new BigDecimal(Objects.toString(raw,"")).intValueExact();if(value<min||value>max)throw new IllegalArgumentException();return value; }
        catch(Exception e){throw new IllegalArgumentException(key+" 须为 "+min+" 至 "+max+" 的整数");}
    }
    private Map<String,Object> decode(Object value) {try{return json.readValue(value.toString(),new TypeReference<>(){});}catch(Exception e){throw new IllegalStateException("题目数据异常");}}
    private Map<String,Object> inflate(Map<String,Object> row) {
        Map<String,Object> result=new LinkedHashMap<>(row);
        result.put("content",decode(result.remove("content_json")));return result;
    }
    public Map<String,Object> list(int user,boolean admin,Map<String,String> params) {
        String scope=params.getOrDefault("scope","public");
        StringBuilder where=new StringBuilder(" WHERE 1=1");List<Object> args=new ArrayList<>();
        if(admin) { if(params.containsKey("status") && !params.get("status").isBlank()){where.append(" AND status=?");args.add(params.get("status"));} }
        else if(scope.equals("mine")){where.append(" AND owner_id=?");args.add(user);}
        else {where.append(" AND status='approved'");}
        for(String key:List.of("subject","grade","question_type","difficulty")) {
            String value=params.get(key);if(value!=null&&!value.isBlank()){where.append(" AND "+key+"=?");args.add(value);}
        }
        String keyword=params.get("keyword");
        if(keyword!=null&&!keyword.isBlank()) { if(keyword.length()>120)throw new IllegalArgumentException("搜索词过长");where.append(" AND (stem LIKE ? OR knowledge_points LIKE ?)");args.add("%"+keyword+"%");args.add("%"+keyword+"%"); }
        int page=Math.max(1,Integer.parseInt(params.getOrDefault("page","1"))),size=Math.min(50,Math.max(1,Integer.parseInt(params.getOrDefault("size","12"))));
        long total=db.queryForObject("SELECT COUNT(*) FROM qb_question"+where,Long.class,args.toArray());
        args.add(size);args.add((long)(page-1)*size);
        List<Map<String,Object>> items=db.queryForList("SELECT * FROM qb_question"+where+" ORDER BY id DESC LIMIT ? OFFSET ?",args.toArray()).stream().map(this::inflate).toList();
        return Map.of("items",items,"total",total,"page",page,"size",size);
    }
    private Map<String,Object> question(long id,boolean lock) {
        List<Map<String,Object>> rows=db.queryForList("SELECT * FROM qb_question WHERE id=?"+(lock?" FOR UPDATE":""),id);
        if(rows.isEmpty())throw new IllegalArgumentException("题目不存在");return rows.get(0);
    }
    public Map<String,Object> detail(long id,int user,boolean admin) {
        Map<String,Object> row=question(id,false);
        if(!admin && !row.get("status").equals("approved") && ((Number)row.get("owner_id")).intValue()!=user)throw new IllegalArgumentException("无权查看此题目");
        Map<String,Object> result=inflate(row);
        if(admin || ((Number)row.get("owner_id")).intValue()==user)result.put("reviews",db.queryForList("SELECT decision,note,question_revision,created_at FROM qb_review WHERE question_id=? ORDER BY id DESC",id));
        return result;
    }
    @SuppressWarnings("unchecked")
    public Map<String,Object> validateQuestion(Map<String,Object> body,boolean complete) {
        Map<String,Object> clean=new LinkedHashMap<>();
        for(String key:List.of("subject","grade","question_type","difficulty"))clean.put(key,text(body,key,40,true));
        String type=clean.get("question_type").toString();
        if(!Set.of("single","multiple","judgment","blank","short","calculation").contains(type))throw new IllegalArgumentException("不支持的题型");
        if(!Set.of("easy","medium","hard").contains(clean.get("difficulty")))throw new IllegalArgumentException("难度无效");
        clean.put("stem",text(body,"stem",10000,complete));clean.put("knowledge_points",text(body,"knowledge_points",500,false));
        clean.put("analysis",text(body,"analysis",10000,complete));
        clean.put("formula",text(body,"formula",2000,false));clean.put("chemical",text(body,"chemical",2000,false));
        Object raw=body.getOrDefault("options",List.of());
        if(!(raw instanceof List<?> list) || list.size()>8)throw new IllegalArgumentException("选项格式错误");
        List<String> options=new ArrayList<>();for(Object option:(List<?>)raw){if(!(option instanceof String s)||(complete&&s.isBlank())||s.length()>2000)throw new IllegalArgumentException("选项不能为空或过长");options.add(s.trim());}
        clean.put("options",options);
        String answer=text(body,"answer",5000,complete);clean.put("answer",answer);
        if(type.equals("single")||type.equals("multiple")) {
            if(options.size()<2)throw new IllegalArgumentException("选择题至少需要两个选项");
            if(!answer.isEmpty()) {
                String normalized=answer.replace(" ","").toUpperCase(Locale.ROOT);
                String[] selected=normalized.split(",",-1);Set<String> seen=new HashSet<>();
                for(String choice:selected)if(choice.length()!=1 || choice.charAt(0)<'A'||choice.charAt(0)>='A'+options.size()||!seen.add(choice))throw new IllegalArgumentException("答案需为有效选项字母，多选用逗号分隔");
                if(type.equals("single") && selected.length!=1)throw new IllegalArgumentException("单选题只能有一个答案");
                if(type.equals("multiple") && selected.length<2)throw new IllegalArgumentException("多选题至少选择两个正确答案");clean.put("answer",normalized);
            }
        }
        if(type.equals("judgment")&&!answer.isEmpty()&&!Set.of("正确","错误").contains(answer))throw new IllegalArgumentException("判断题答案须为正确或错误");
        return clean;
    }
    private long insert(String sql,Object... args) {
        GeneratedKeyHolder keys=new GeneratedKeyHolder();db.update(conn->{var stmt=conn.prepareStatement(sql,new String[]{"id"});for(int i=0;i<args.length;i++)stmt.setObject(i+1,args[i]);return stmt;},keys);
        return Objects.requireNonNull(keys.getKey()).longValue();
    }
    @Transactional public Map<String,Object> saveQuestion(Long id,int user,Map<String,Object> body,boolean admin) {
        String action=text(body,"action",20,true);
        if(!Set.of("draft","submit","publish").contains(action)||(!admin&&action.equals("publish")))throw new IllegalArgumentException("保存操作无效");
        Map<String,Object> content=validateQuestion(body,!action.equals("draft"));
        String status=action.equals("publish")?"approved":action.equals("submit")?"pending":"draft";
        if(id==null)id=insert("INSERT INTO qb_question(owner_id,subject,grade,question_type,difficulty,stem,knowledge_points,content_json,status) VALUES(?,?,?,?,?,?,?,?,?)",user,content.get("subject"),content.get("grade"),content.get("question_type"),content.get("difficulty"),content.get("stem"),content.get("knowledge_points"),encode(content),status);
        else {
            Map<String,Object> old=question(id,true);
            if(!admin&&((Number)old.get("owner_id")).intValue()!=user)throw new IllegalArgumentException("无权修改此题目");
            if(!admin&&!Set.of("draft","rejected").contains(old.get("status")))throw new IllegalArgumentException("审核中或公开题目不可修改，请复制为新题投稿");
            if(((Number)old.get("revision")).intValue()!=integer(body,"revision",0,1,Integer.MAX_VALUE))throw new IllegalArgumentException("题目已更新，请刷新后重试");
            db.update("UPDATE qb_question SET subject=?,grade=?,question_type=?,difficulty=?,stem=?,knowledge_points=?,content_json=?,status=?,review_note='',reviewer_id=NULL,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?",content.get("subject"),content.get("grade"),content.get("question_type"),content.get("difficulty"),content.get("stem"),content.get("knowledge_points"),encode(content),status,id);
        }
        if(admin&&action.equals("publish"))db.update("INSERT INTO qb_review(question_id,reviewer_id,decision,note,question_revision) SELECT id,?,'approved','后台直接发布',revision FROM qb_question WHERE id=?",user,id);
        return detail(id,user,admin);
    }
    @Transactional public Map<String,Object> review(long id,int admin,Map<String,Object> body) {
        String decision=text(body,"decision",20,true),note=text(body,"note",1000,false);
        if(!Set.of("approved","rejected","withdrawn").contains(decision))throw new IllegalArgumentException("审核决定无效");
        if(!decision.equals("approved")&&note.isBlank())throw new IllegalArgumentException("请填写退回或下架原因");
        Map<String,Object> old=question(id,true);
        if(!Objects.equals(old.get("status"),decision.equals("withdrawn")?"approved":"pending"))throw new IllegalArgumentException("题目状态已变化，请刷新");
        if(((Number)old.get("revision")).intValue()!=integer(body,"revision",0,1,Integer.MAX_VALUE))throw new IllegalArgumentException("题目版本已变化");
        if(decision.equals("approved"))validateQuestion(decode(old.get("content_json")),true);
        String status=decision.equals("withdrawn")?"rejected":decision;
        db.update("UPDATE qb_question SET status=?,review_note=?,reviewer_id=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?",status,note,admin,id);
        db.update("INSERT INTO qb_review(question_id,reviewer_id,decision,note,question_revision) VALUES(?,?,?,?,?)",id,admin,decision,note,old.get("revision"));
        return detail(id,admin,true);
    }
    public List<Map<String,Object>> papers(int user) {return db.queryForList("SELECT id,title,subject,duration_minutes,total_score,revision,updated_at FROM qb_paper WHERE owner_id=? ORDER BY updated_at DESC,id DESC",user);}
    public Map<String,Object> paper(long id,int user) {
        List<Map<String,Object>> rows=db.queryForList("SELECT * FROM qb_paper WHERE id=? AND owner_id=?",id,user);
        if(rows.isEmpty())throw new IllegalArgumentException("试卷不存在或无权访问");return inflate(rows.get(0));
    }
    @Transactional public Map<String,Object> savePaper(Long id,int user,Map<String,Object> body) {
        String title=text(body,"title",120,true),subject=text(body,"subject",40,true);
        int duration=integer(body,"duration_minutes",45,5,300);
        Object raw=body.get("items");if(!(raw instanceof List<?> items)||items.isEmpty()||items.size()>100)throw new IllegalArgumentException("每份试卷请选择1至100道题");
        Map<String,Object> existing=id==null?null:paper(id,user);
        Map<Long,Map<String,Object>> frozen=new HashMap<>();
        if(existing!=null)for(Object item:(List<?>)((Map<?,?>)existing.get("content")).get("items")){
            Map<String,Object> i=(Map<String,Object>)item;frozen.put(((Number)i.get("question_id")).longValue(),i);
        }
        List<Map<String,Object>> snapshots=new ArrayList<>();Set<Long> seen=new HashSet<>();BigDecimal total=BigDecimal.ZERO;
        for(Object rawItem:items) {
            if(!(rawItem instanceof Map<?,?> item)||!(item.get("question_id") instanceof Number))throw new IllegalArgumentException("题目参数无效");
            long qid;try{qid=new BigDecimal(item.get("question_id").toString()).longValueExact();if(qid<=0)throw new IllegalArgumentException();}catch(Exception e){throw new IllegalArgumentException("题目编号须为正整数");}if(!seen.add(qid))throw new IllegalArgumentException("试卷中题目重复");
            BigDecimal score;try{score=new BigDecimal(item.get("score").toString());}catch(Exception e){throw new IllegalArgumentException("分值无效");}
            if(score.signum()<=0||score.compareTo(new BigDecimal("100"))>0||score.scale()>2)throw new IllegalArgumentException("每题分值须大于0、不超过100，最多两位小数");
            Map<String,Object> snapshot=new LinkedHashMap<>();
            if(frozen.containsKey(qid))snapshot.putAll(frozen.get(qid));
            else {
                Map<String,Object> q=question(qid,true);
                boolean own=((Number)q.get("owner_id")).intValue()==user;
                if(!q.get("status").equals("approved")&&!(own&&q.get("status").equals("draft")))throw new IllegalArgumentException("所选题目未公开或已下架");
                Map<String,Object> content=decode(q.get("content_json"));validateQuestion(content,true);
                snapshot.put("question",content);snapshot.put("source_revision",q.get("revision"));
            }
            if(!Objects.equals(((Map<?,?>)snapshot.get("question")).get("subject"),subject))throw new IllegalArgumentException("同一份试卷请选择相同学科的题目");
            snapshot.put("question_id",qid);snapshot.put("score",score);snapshots.add(snapshot);total=total.add(score);
        }
        String payload=encode(Map.of("items",snapshots));
        if(id==null)id=insert("INSERT INTO qb_paper(owner_id,title,subject,duration_minutes,total_score,content_json) VALUES(?,?,?,?,?,?)",user,title,subject,duration,total,payload);
        else if(db.update("UPDATE qb_paper SET title=?,subject=?,duration_minutes=?,total_score=?,content_json=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_id=? AND revision=?",title,subject,duration,total,payload,id,user,integer(body,"revision",0,1,Integer.MAX_VALUE))!=1)throw new IllegalArgumentException("试卷已更新，请刷新后重试");
        return paper(id,user);
    }
}
