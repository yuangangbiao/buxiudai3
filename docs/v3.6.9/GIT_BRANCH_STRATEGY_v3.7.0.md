# Git 分支策略文档 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P1 文档，Week 0 第1天必须建立
> **审计来源**: 4专家审计（小圣架构）→ O-3

---

## 一、问题背景

18周重构（v3.7.0）期间，生产系统（v3.6.9）仍需维护bug修复和新功能。如何在重构分支与主分支之间保持同步，同时不让重构分支被生产需求污染，是核心问题。

---

## 二、分支模型

### 2.1 分支结构

```
main  ────────────────────────────── 生产环境
 │                                          ↑
 │  merge（生产bug修复 + 紧急功能）           │  git revert / 回滚
 │                                          │
 │  ←──── merge（P0安全修复等紧急补丁）────←  │
 │                                          │
 └────────────┬───────────────────────────────┘
              │ merge（v3.7.0完成，所有gate通过）
              ↓
v3.7.0-refactor  ←── feature/v3.7.0-*  ←── 重构任务分支
                │
                ├── feature/v3.7.0-P0-G           （P0安全修复）
                ├── feature/v3.7.0-layer1-app     （app.py 26处）
                ├── feature/v3.7.0-layer1-report  （report_record 20处）
                ├── feature/v3.7.0-layer1-others  （其他4处）
                ├── feature/v3.7.0-layer2-dao     （DAO抽象）
                ├── feature/v3.7.0-layer3-repo    （Repository抽象）
                ├── feature/v3.7.0-phase3-cloudpoller  （CloudPoller）
                ├── feature/v3.7.0-phase3-core-split     （_core.py拆分）
                └── feature/v3.7.0-phase3-waitress     （waitress迁移）
```

### 2.2 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|---------|---------|------|
| 重构主分支 | `v3.7.0-refactor` | `v3.7.0-refactor` |
| 重构任务分支 | `feature/v3.7.0-{task-id}` | `feature/v3.7.0-P0-G` |
| 生产bug修复 | `hotfix/v3.6.9-{bug-id}` | `hotfix/v3.6.9-login-fix` |
| 生产功能分支 | `feature/v3.6.9-{feature-id}` | `feature/v3.6.9-new-report` |
| 主分支 | `main` | `main` |

---

## 三、日常开发规则

### 3.1 重构期间（Week 0-19）

**规则1**：重构开发在 `v3.7.0-refactor` 分支进行，禁止在 main 分支提交任何重构代码。

**规则2**：每个重构任务（Layer1第一批/Layer1第二批/Phase3等）从 `v3.7.0-refactor` 拉出独立任务分支。

```bash
# 每天开始工作前
git checkout v3.7.0-refactor
git pull origin v3.7.0-refactor  # 同步最新代码

# 开始新任务
git checkout -b feature/v3.7.0-layer1-app
# ... 开发中 ...
git push origin feature/v3.7.0-layer1-app

# 任务完成后，PR到 v3.7.0-refactor
# PR必须通过4-gate门禁才能合并
```

**规则3**：每次合并到 `v3.7.0-refactor` 前，必须 rebase（禁止 merge），保持线性历史。

```bash
git checkout feature/v3.7.0-layer1-app
git fetch origin
git rebase origin/v3.7.0-refactor  # 保持线性
git push --force  # 仅对自己分支可force
```

### 3.2 生产维护期间（Week 0-19 同时）

**规则4**：生产bug修复从 `main` 拉出 hotfix 分支，修复后直接合并回 `main`，并同步到 `v3.7.0-refactor`。

```bash
# 生产发现bug，从main拉hotfix
git checkout main
git pull origin main
git checkout -b hotfix/v3.6.9-{bug-id}

# ... 修复bug ...
git checkout main
git merge hotfix/v3.6.9-{bug-id} --no-ff
git tag v3.6.9-hotfix-{date}
git push origin main

# 同步到重构分支
git checkout v3.7.0-refactor
git cherry-pick {修复commit的hash}  # 选择性同步
# 或：git merge hotfix/v3.6.9-{bug-id} --no-ff
```

**规则5**：生产新功能（与重构无关）从 `main` 拉出 feature 分支，合并后同步到 `v3.7.0-refactor`（如果需要）。

```bash
git checkout main
git checkout -b feature/v3.6.9-{feature}
# ... 开发新功能 ...
git checkout main
git merge feature/v3.6.9-{feature} --no-ff
git push origin main

# 同步到重构分支
git checkout v3.7.0-refactor
git merge origin/main  # 同步main最新
```

---

## 四、冲突处理规则

### 4.1 重构分支 vs 生产分支冲突

**场景**：生产修复的某个文件与重构分支修改的同一文件产生冲突。

**处理原则**：
- 如果是**重构改动的部分**有冲突 → 重构方负责解决，保留重构逻辑
- 如果是**生产修复**有冲突 → 保留生产修复逻辑，重构方适配

**禁止**：为解决冲突而回退已通过4-gate门禁的代码。

### 4.2 冲突解决流程

```bash
# 1. 在重构任务分支解决冲突
git checkout feature/v3.7.0-layer1-app
git rebase origin/v3.7.0-refactor

# 2. 解决冲突后，重新跑4-gate门禁
pytest tests/ -v  # 验证
python -m bandit -r mobile_api_ai -ll  # 安全扫描

# 3. 强制推送到任务分支
git push --force-with-lease origin feature/v3.7.0-layer1-app
```

---

## 五、发布与回滚

### 5.1 重构完成发布

```bash
# v3.7.0-refactor 全部gate通过后
git checkout v3.7.0-refactor
git tag v3.7.0-RC1  # Release Candidate
git push origin v3.7.0-refactor
git push origin v3.7.0-RC1

# 合并到main
git checkout main
git merge v3.7.0-refactor --no-ff -m "Merge v3.7.0 refactor"
git tag v3.7.0
git push origin main
git push origin v3.7.0
```

### 5.2 回滚流程

```bash
# 生产环境回滚（立即）
git checkout main
git revert {bad_commit_hash}  # 生成回滚commit
git tag v3.7.0-rollback-{date}
git push origin main

# 重构分支同步（24小时内）
git checkout v3.7.0-refactor
git revert {bad_commit_hash}
git push origin v3.7.0-refactor
```

### 5.3 紧急回滚条件

| 条件 | 操作 | 允许时间 |
|------|------|---------|
| API错误率 > 5% | git revert + 重新部署 | ≤ 10分钟 |
| 特定接口完全失败 | 部分回滚（git revert特定文件） | ≤ 15分钟 |
| P99响应 > 3秒 | 回滚 + 性能分析 | ≤ 30分钟 |

---

## 六、Hotfix并行处理（重构期间生产Bug修复）

> 重构期间（Week 0-19），生产系统（main分支）仍可能出Bug。hotfix处理需要与重构分支并行进行。

### 6.1 Hotfix决策矩阵

| 场景 | 从哪个分支拉 | 修复后合并到 | 同步到v3.7.0-refactor |
|------|------------|------------|----------------------|
| 生产P0 Bug（紧急） | `main` | `main` 立即 | cherry-pick（48小时内） |
| 生产P1 Bug | `main` | `main` | merge 或 cherry-pick |
| 重构引入的Bug | `v3.7.0-refactor` | `v3.7.0-refactor` | N/A |
| Bug涉及的文件正好在重构中 | 优先在 `v3.7.0-refactor` 修 | 重构分支通过Gate后合并main | 重构修完=生产修完 |

### 6.2 生产P0 Hotfix标准流程

```bash
# 1. 从main拉hotfix分支
git checkout main
git pull origin main
git checkout -b hotfix/v3.6.9-{bug-id}

# 2. 修复Bug（改动要小，<3个文件）
# ... 修复代码 ...

# 3. 紧急合并到main（不打tag，因为还在v3.6.x）
git add .
git commit -m "hotfix: {一句话描述} refs #{bug-id}"
git checkout main
git merge hotfix/v3.6.9-{bug-id} --no-ff -m "Merge hotfix v3.6.9-{bug-id}"
git push origin main

# 4. 部署生产（立即）
# ... 部署命令 ...

# 5. 48小时内同步到v3.7.0-refactor
git checkout v3.7.0-refactor
git cherry-pick {hotfix_commit_hash}
# 或：git merge hotfix/v3.6.9-{bug-id} --no-ff（如果冲突少）

# 6. 跑Gate1验证
pytest tests/ -v
bandit -r mobile_api_ai -ll

# 7. 推送v3.7.0-refactor
git push origin v3.7.0-refactor
```

### 6.3 重构引入Bug的处理

```bash
# 如果Bug是在v3.7.0-refactor引入的：
# 1. 在v3.7.0-refactor的当前任务分支上修复
git checkout feature/v3.7.0-layer1-app
# ... 修复Bug ...

# 2. 验证Gate
pytest tests/ -v
# ... 通过后 ...

# 3. 推送（触发CI）
git push --force-with-lease origin feature/v3.7.0-layer1-app

# 4. 不要合入main（重构完成前main是生产稳定版）
```

### 6.4 冲突处理规则

当hotfix与重构改动同一文件时：
- 优先保留**生产环境的正确逻辑**（hotfix的改动是为了修Bug）
- 但如果重构改动的API/接口变了，hotfix需要同步适配
- **禁止**在hotfix中回退已通过4-gate的重构代码

### 6.5 Hotfix禁止事项

| 禁止项 | 原因 |
|--------|------|
| 禁止在hotfix分支做架构改造 | hotfix应该小而快 |
| 禁止在hotfix中引入新依赖 | 增加生产风险 |
| 禁止跳过测试直接部署 | 必须跑pytest |
| 禁止在重构完成前合入main | 保护生产稳定性 |

---

## 七、生产需求插入规则

重构期间，如果生产有新功能需求（与重构无关）：

```bash
# 从main拉分支开发
git checkout main
git checkout -b feature/v3.6.9-{feature-name}

# ... 开发新功能 ...

# 合并到main
git checkout main
git merge feature/v3.6.9-{feature-name} --no-ff
git tag v3.6.9-{n}
git push origin main
git push origin v3.6.9-{n}

# 同步到v3.7.0-refactor（Week 19前）
git checkout v3.7.0-refactor
git merge origin/main --no-ff  # 同步main最新
# 如果有冲突，按"保留重构逻辑"处理
```

**注意**：如果新功能涉及的文件也在重构范围内（如涉及 process.bp），需要评估是否在重构完成后再合入，避免冲突。

---

## 八、分支生命周期

| 分支 | 创建时机 | 合并时机 | 合并后 |
|------|---------|---------|-------|
| `feature/v3.7.0-P0-G` | Week 0 | Gate1-4全通过 | 删除分支 |
| `feature/v3.7.0-layer1-app` | Week 3 | Gate1-4全通过 | 删除分支 |
| `feature/v3.7.0-layer1-report` | Week 5 | Gate1-4全通过 | 删除分支 |
| `feature/v3.7.0-layer1-others` | Week 7 | Gate1-4全通过 | 删除分支 |
| `feature/v3.7.0-layer2-*` | Week 11 | Gate1-4全通过 | 删除分支 |
| `feature/v3.7.0-phase3-*` | Week 13 | Gate1-4全通过 | 删除分支 |
| `hotfix/v3.6.9-*` | 生产Bug时 | 立即合main | 48小时内同步 |
| `v3.7.0-refactor` | Week 0 | Week 19全部完成 | 成为新main |

---

## 九、签字确认

| 签字人 | 职责 | 签字 |
|--------|------|------|
| 开发负责人 | 熟悉分支策略，执行规范 | ☐ |
| 架构（小圣） | 审核冲突处理方案 | ☐ |
| PM（小曦） | 确认生产需求插入规则 | ☐ |

**建立截止**: Week 0 第1天
**最后更新**: 2026-06-28
