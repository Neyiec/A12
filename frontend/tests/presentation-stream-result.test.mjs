import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { restoreStreamedPresentation, isServerValidatedHtml, mapLimited } from '../src/utils/presentationStreamResult.js'
import { readFileSync } from 'node:fs'
import { babelParse } from '@vue/compiler-sfc'
import vm from 'node:vm'

test('流式最终响应重组已接收HTML，保留最终校验信息且拒绝缺页', () => {
  const final={stream_compact:true,slide_count:1,slides:[{slide_no:1,title:'最终标题',metadata:{html_validation:{valid:true}}}]}
  const received=new Map([[1,{slide_no:1,html:'<html>完整页面</html>',metadata:{theme:'blue'}}]])
  const result=restoreStreamedPresentation(final,received)
  assert.equal(result.slides[0].html,'<html>完整页面</html>')
  assert.equal(result.slides[0].title,'最终标题')
  assert.equal(result.slides[0].metadata.theme,'blue')
  assert.equal(result.slides[0].metadata.html_validation.valid,true)
  assert.throws(()=>restoreStreamedPresentation(final,new Map()),/结果缺失/)
  assert.equal(restoreStreamedPresentation({slides:[]},received).slides.length,0)
})

test('仅字节一致的服务器已校验HTML可以省去重复请求，编辑后重新校验', async () => {
  const digest=async text=>createHash('sha256').update(text).digest('hex')
  const slide={html:'<html>原始内容</html>',metadata:{html_validation:{valid:true,sha256:await digest('<html>原始内容</html>')}}}
  assert.equal(await isServerValidatedHtml(slide,digest),true)
  assert.equal(await isServerValidatedHtml({...slide,html:'<html>修改后</html>'},digest),false)
  assert.equal(await isServerValidatedHtml({html:slide.html},digest),false)
})

test('校验并发受限且结果保序', async () => {
  let active=0,maximum=0
  const result=await mapLimited([1,2,3,4,5],2,async item=>{
    active++;maximum=Math.max(maximum,active)
    await new Promise(resolve=>setImmediate(resolve))
    active--;return item*2
  })
  assert.deepEqual(result,[2,4,6,8,10])
  assert.equal(maximum,2)
})

test('真实SSE读取函数请求精简传输并重组完整结果', async () => {
  const source=readFileSync(new URL('../src/apis/teacher.js',import.meta.url),'utf8')
  const declaration=babelParse(source,{sourceType:'module'}).program.body.find(node=>node.type==='ExportNamedDeclaration' && node.declaration?.id?.name==='generatePresentationStream').declaration
  const code=source.slice(declaration.start,declaration.end).replaceAll('import.meta.env.VITE_PYTHON_API_BASE_URL',"''")
  const body='event: presentation_slide\ndata: '+JSON.stringify({slide:{slide_no:1,html:'<html>完整页面</html>'}})+'\n\nevent: final\ndata: '+JSON.stringify({stream_compact:true,slide_count:1,slides:[{slide_no:1,title:'完成'}]})+'\n\n'
  let requested
  const context={useUserStore:()=>({token:'test-only'}),restoreStreamedPresentation,TextDecoder,Uint8Array,Map,
    fetch:async (_,options)=>{requested=JSON.parse(options.body);return {ok:true,body:new ReadableStream({start(c){c.enqueue(new TextEncoder().encode(body));c.close()}})}}}
  const generate=vm.runInNewContext(code+';generatePresentationStream',context)
  const result=await generate({title:'函数'})
  assert.equal(requested.stream_compact,true)
  assert.equal(result.slides[0].html,'<html>完整页面</html>')
})
