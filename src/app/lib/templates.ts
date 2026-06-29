// 高频任务模板：点击即填入输入框，降低上手成本

export interface TaskTemplate {
  title: string;
  description: string;
  task: string;
  icon: string;
}

export const TASK_TEMPLATES: TaskTemplate[] = [
  {
    title: "分析项目结构",
    description: "列出目录、识别模块、总结架构",
    icon: "📁",
    task: "分析当前项目的目录结构，识别主要模块和它们的作用，最后给出整体架构总结。",
  },
  {
    title: "代码审查",
    description: "扫描代码并给出改进建议",
    icon: "🔍",
    task: "对 backend 和 src 目录下的核心代码进行审查，找出潜在问题（安全、性能、可维护性），给出改进建议。",
  },
  {
    title: "生成 README",
    description: "根据项目现状自动生成文档",
    icon: "📝",
    task: "根据项目的实际代码和配置，生成一份完整的 README.md，包含项目介绍、技术栈、运行方式、目录结构。",
  },
  {
    title: "创建翻译工具",
    description: "演示 Agent 自举新工具能力",
    icon: "🔧",
    task: "创建一个名为 translate_to_en 的工具，用于将中文文本翻译为英文，创建后测试调用一次。",
  },
  {
    title: "检查项目安全",
    description: "扫描命令白名单与权限配置",
    icon: "🛡",
    task: "检查项目的安全配置：命令白名单有哪些、当前角色权限、是否有路径越界风险，给出安全评估报告。",
  },
  {
    title: "统计代码行数",
    description: "按语言统计代码量",
    icon: "📊",
    task: "统计项目各目录下的代码文件数量和总行数，按语言（Python/TypeScript/其他）分类汇总。",
  },
];
