import test from 'node:test'
import assert from 'node:assert/strict'
import { apiErrorMessage, assertApiSuccess, normalizeRequestError, responsePayload } from '../src/utils/apiError.js'
test('HTTP200业务失败不得作为成功继续执行',()=>{
  assert.throws(()=>assertApiSuccess({code:400,message:'请先确认双图谱'}),/确认双图谱/)
  for(const code of [0,200,'200',undefined])assert.doesNotThrow(()=>assertApiSuccess({code,data:[]}))
})
test('验证错误展示具体字段，数据库堆栈不直接暴露给教师',()=>{
  assert.match(apiErrorMessage({detail:[{loc:['body','target_ids'],msg:'Field required'}]},422),/target_ids.*Field required/)
  const message=apiErrorMessage({message:"### Error updating database. java.sql.SQLSyntaxErrorException: Unknown column 'page_version'"},400)
  assert.match(message,/数据库结构/);assert.doesNotMatch(message,/java.sql|page_version/)
})
test('连接、限流和大小限制均有可操作提示',async()=>{
  for(const status of [502,503,504])assert.match(apiErrorMessage(null,status),/后端和数据库/)
  assert.match(apiErrorMessage(null,413),/分批/)
  assert.match(apiErrorMessage(null,429),/频繁/)
  assert.match((await normalizeRequestError(Object.assign(new Error('Network Error'),{request:{}}))).message,/无法连接服务/)
})
test('下载失败的JSON错误不能伪装为导出文件',async()=>{
  const response={data:new Blob([JSON.stringify({code:400,message:'快照版本不存在'})],{type:'application/json'})}
  const data=await responsePayload(response);assert.throws(()=>assertApiSuccess(data,response),/快照版本不存在/)
  const raw={data:new Blob(['pptx'],{type:'application/octet-stream'})};assert.equal(await responsePayload(raw),raw.data)
})
test('保留取消标记和原始响应供调用方识别',async()=>{
  const canceled={code:'ERR_CANCELED',message:'canceled'};assert.equal(await normalizeRequestError(canceled),canceled)
  const response={status:422,data:{detail:'请先保存图谱'}}
  const error=Object.assign(new Error('status422'),{response});assert.equal((await normalizeRequestError(error)).response,response);assert.equal(error.message,'请先保存图谱')
})

test('MySQL截断异常和简化错误不暴露表字段与内部路径',()=>{
  for (const message of ["com.mysql.cj.jdbc.exceptions.MysqlDataTruncation: Data too long for column 'private_column'", "Data too long for column 'private_column'"]) {
    const safe=apiErrorMessage({message},500)
    assert.match(safe,/数据服务异常/)
    assert.doesNotMatch(safe,/private_column|com.mysql/)
  }
})
