import path from "node:path";
import { pathToFileURL } from "node:url";

const workspaceDir = "D:\\GitRepositories\\A12";
const skillDir = "C:\\Users\\32761\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.909.12148\\skills\\presentations";
const candidatePath = path.join(workspaceDir, "artifacts", "ppt-benchmark", "光合作用-qwen3.7-flash-可编辑-v5.pptx");
const finalPath = path.join(workspaceDir, "artifacts", "ppt-benchmark", "光合作用-PPT生成联调测试-可编辑.pptx");
const receiptPath = path.join(workspaceDir, ".codex-finalizer", "ppt-benchmark-delivery.validation.json");

const { finalizePresentation } = await import(pathToFileURL(
  path.join(skillDir, "container_tools", "artifact_tool_utils.mjs"),
).href);

const result = await finalizePresentation({
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: "C:\\Users\\32761\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe",
  integrityValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "9144000,5143500",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  explicitTotalSlideCount: 8,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  verifyArtifactToolImport: true,
  receiptPath,
});

console.log(JSON.stringify(result, null, 2));
