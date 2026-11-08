import test from 'node:test'
import assert from 'node:assert/strict'
import { addToBasket, totalScore, paperItems, emptyQuestion } from '../src/utils/questionBank.js'
test('题篮禁止跨学科与重复题目',()=>{
  const first={id:1,subject:'数学',question_type:'single'}
  const items=addToBasket([],first)
  assert.equal(items[0].score,3)
  assert.equal(addToBasket(items,first),items)
  assert.throws(()=>addToBasket(items,{id:2,subject:'化学'}),/同一学科/)
})
test('题篮限制100题',()=>assert.throws(()=>addToBasket(Array.from({length:100},(_,id)=>({id,subject:'数学'})),{id:101,subject:'数学'}),/100/))
test('分值统计不会出现浮点尾数',()=>assert.equal(totalScore([{score:.1},{score:.2}]),.3))
test('打开试卷使用服务端固定快照而不是题库当前内容',()=>{
  const items=paperItems({content:{items:[{question_id:7,score:'5.00',source_revision:2,question:{stem:'历史题干',subject:'数学'}}]}})
  assert.deepEqual(items,[{id:7,score:5,source_revision:2,stem:'历史题干',subject:'数学'}])
})
test('新建题目实例不共享选项数组',()=>{const a=emptyQuestion(),b=emptyQuestion();a.options[0]='changed';assert.equal(b.options[0],'')})
