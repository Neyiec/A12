import test from 'node:test'
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFileSync } from 'node:fs'
import { parse, babelParse } from '@vue/compiler-sfc'
import * as vue from 'vue'

const script = parse(readFileSync(new URL('../src/components/CreationWorkspace.vue', import.meta.url), 'utf8')).descriptor.scriptSetup.content
const nodes = babelParse(script, { sourceType: 'module' }).program.body
const code = nodes.filter(n => n.type !== 'ImportDeclaration').map(n => script.slice(n.start, n.end)).join('\n').replaceAll('import.meta.env', '({DEV:false})')

test('生成PPT进入工作台时完整setup执行成功，初始画布已就绪', () => {
  const scope = vue.effectScope()
  const hooks = []
  const sandbox = { console, setTimeout, clearTimeout, setInterval, clearInterval, URL, URLSearchParams, structuredClone,
    window:{ innerWidth:1440,innerHeight:900,matchMedia:()=>({matches:false,addEventListener(){},removeEventListener(){}}),addEventListener(){},removeEventListener(){},
      localStorage:{getItem:()=>null,setItem(){},removeItem(){}},sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}} },
    document:{documentElement:{dataset:{},style:{setProperty(){}}},addEventListener(){},removeEventListener(){}},
  }
  for (const node of nodes.filter(n => n.type === 'ImportDeclaration')) {
    for (const item of node.specifiers) sandbox[item.local.name] = () => undefined
  }
  Object.assign(sandbox, { ref:vue.ref, reactive:vue.reactive, computed:vue.computed, watch:vue.watch, nextTick:vue.nextTick,
    onMounted:fn=>hooks.push(fn),onBeforeUnmount(){},onBeforeRouteLeave(){},onBeforeRouteUpdate(){},
    useRoute:()=>({query:{sessionId:'16',pptGeneration:'local-test',resourceIds:'[]',workspaceContext:'{}'}}),
    useRouter:()=>({push(){},replace(){}}),useUserStore:()=>({userInfo:{user_id:1}}),
    INTERACTIVE_MODULE_TYPES:[],subjectToolRuntimeCss:'',
  })
  sandbox.localStorage = sandbox.window.localStorage
  sandbox.sessionStorage = sandbox.window.sessionStorage
  try {
    const result = scope.run(() => vm.runInNewContext(`(() => {${code};return {html:structuredHtmlCanvasSource.value,hooksReady:true}})()`, sandbox, {filename:'CreationWorkspace.setup.js'}))
    assert.equal(result.hooksReady,true)
    assert.match(result.html, /<html/)
    assert.ok(hooks.length)
  } finally { scope.stop() }
})
