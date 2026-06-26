# PROJECT_CONSTITUTION

> 使用方式：复制到项目的 `docs/PROJECT_CONSTITUTION.md`，填写项目不可违反的硬规则。该文件约束计划、执行、审查和验收。

## MUST

- 项目必须遵守的硬规则。
- 违反后不得进入验收或合并。

## SHOULD

- 推荐遵守的工程习惯。
- 违反后需要说明原因。

## MUST NOT

- 明确禁止事项。
- 违反后应标记 P0/P1。

## Review 映射

| Constitution 规则 | 违反时默认严重等级 |
| --- | --- |
| MUST | P0 / P1 |
| SHOULD | P2 |
| MUST NOT | P0 / P1 |

## 与其他项目文件的区别

| 文件 | 用途 |
| --- | --- |
| `PROJECT_CONSTITUTION.md` | 项目不可违反的原则和硬规则 |
| `CODE_REVIEW_CHECKLIST.md` | 审查代码时的检查项 |
| `DECISIONS.md` | 重大架构 / 方向 / 依赖决策记录 |
| `PROJECT_INDEX.md` | 项目入口、目录、运行方式索引 |
| `docs/memory/` | 可复用项目知识和踩坑经验 |

## 建议维护规则

- 只记录长期有效的硬规则。
- 不把临时偏好写成 MUST。
- 修改 MUST / MUST NOT 前应用户确认。
- 审查任务应检查当前 diff 是否违反 Constitution。
- 如果 Constitution 与实际代码冲突，标记冲突并等待用户确认，不要编造现状。
