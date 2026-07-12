# Workflow Contract Golden Fixtures

本目录是 v0.7 Reader、Validator 与 lint 的只读测试 oracle，不是 TASK 状态真相源。

- `valid/`：严格 v0.7 合法输入。
- `violations/`：结构错误与跨轴不变量反例。
- `legacy/`：显式 legacy 映射与冲突。
- `comparisons/`：基于真实 Git 变更回填的 Legacy/Compact 填写量对比。
- `projects/`：公开 project-root 目录形状。

`manifest.json` 固定输入路径、期望 normalized 字段、精确 diagnostics 与启用阶段。后续实现不得为“让测试通过”修改 oracle；若规范确有冲突，应回到 CONTRACT-001。

所有路径均相对本目录，所有样本均为公开仓库内容，不含本机路径或私有业务数据。
