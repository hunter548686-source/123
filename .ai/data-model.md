# 数据模型增量（本轮）

## TaskStatus
- 新增：
  - `cancelling`
  - `cleaning_up`

## TaskRunStatus
- 新增：
  - `cancelling`
  - `cleaning_up`
  - `cancelled`

## Artifact
- 新增字段：
  - `download_url`
  - `checksum`
  - `metadata_payload`

## 关联影响
- 任务详情接口中的 artifact 输出扩展。
- worker 在 cancel/failure/success 后都可触发 cleanup 事件链。
