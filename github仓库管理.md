###  场景一：开发一个全新的功能

**1. 同步最新代码并创建新分支**

```bash
# 切换到主分支
git checkout main
# 拉取其他成员昨天的最新代码
git pull origin main
# 基于最新的 main 创建自己的功能分支
git checkout -b feature/login
```

**2. 开发中：随时保存**
写完一部分代码（比如调通了一个接口），就提交一次：

```bash
git add -A
git commit -m "feat: 完成登录页面的UI布局"
```

**3. 每天收工：推送代码并发起 PR**

```bash
# 将自己的分支推送到 GitHub
git push origin feature/login
```

推送成功后，去 GitHub 网页上点击黄色的 **"Compare & pull request"** 按钮，创建 PR。

> **注意**：如果功能没开发完，请务必点击绿色按钮旁边的下拉箭头，选择 **"Create draft pull request"** 创建草稿 PR，防止队友误合并。

------

### 场景二：继续开发昨天没写完的功能

如果你昨天已经创建了分支，但功能没写完，今天**不需要**重新切回 `main` 创建分支，直接接着写即可：

**1. 切回你的功能分支**

```bash
# 直接切换到你昨天没写完的分支
git checkout feature/login
```

**2. 同步队友的最新进度（防止冲突）**

```bash
# 把队友昨天合并到 main 的新代码，同步到你当前的分支里
git pull origin main
```

**3. 接着昨天的代码继续开发**
直接打开编辑器继续写，写完后正常提交和推送：

```bash
git add .
git commit -m "feat: 接入登录API接口"
git push origin feature/login
```

> 推送后，GitHub 上昨天的那个草稿 PR 会自动更新包含你新提交的代码。

------

### PR 提交规范

采用 **“类型: 具体描述”** 的格式：

- **feat**: 新功能（例如：`feat: 增加用户登录页面UI`）
- **fix**: 修复 Bug（例如：`fix: 修复首页轮播图无法自动播放的问题`）
- **docs**: 文档更新（例如：`docs: 更新README部署说明`）
- **style**: 格式调整（不影响代码运行的变动，例如：`style: 调整代码缩进和空格`）
- **refactor**: 重构（既不是新增功能，也不是修改bug的代码变动）
- **chore**: 构建过程或辅助工具的变动（例如：`chore: 更新依赖包版本`）

**具体描述模板：**

```markdown
### 变更目的
<!-- 简单说明这个 PR 解决了什么问题，或者实现了什么功能 -->

### 主要改动
- 改动了 A 文件的 xxx 逻辑
- 新增了 B 组件
- 删除了 C 接口

### 验证方式
- [ ] 本地运行无报错
- [ ] 核心功能测试通过
- [ ] 已检查无敏感信息泄露（如密码、密钥等）

### 截图（可选）
<!-- 如果是前端 UI 改动，建议贴上修改前后的对比图 -->
```

------

### 分支命名规范

采用 **“类型/具体描述”** 的格式：

- **feat**/新功能（例如：`feat: 增加用户登录页面UI`）
- **fix**/修复 Bug（例如：`fix: 修复首页轮播图无法自动播放的问题`）
- **docs**/文档更新（例如：`docs: 更新README部署说明`）
- **style**/格式调整（不影响代码运行的变动，例如：`style: 调整代码缩进和空格`）
- **refactor**/重构（既不是新增功能，也不是修改bug的代码变动）
- **chore**/构建过程或辅助工具的变动（例如：`chore: 更新依赖包版本`）

### 收尾：代码审查与合并

- 当功能开发完毕，在草稿 PR 页面点击 **"Ready for review"** 转为正式 PR。
- 别的合作者在网页上查看代码，没问题就点击 **Merge pull request**。
- 合并后，可以在网页上点击 **Delete branch** 删除远程分支。

**本地清理：删除旧分支**

```bash
# 切回主分支，并拉取刚刚合并的新代码
git checkout main
git pull origin main
# 删除本地已经用完的旧分支
git branch -d feature/login
```

------

### 突发情况处理

**1. 发生代码冲突（Conflict）怎么办？**
如果两个人同时修改了同一个文件的同一行，合并时就会冲突。

- 在本地执行 `git pull origin main`，Git 会标记出冲突的地方（`<<<<<<<` 和 `>>>>>>>`）。
- 打开文件，手动保留正确的代码，删除冲突标记。
- 重新执行 `git add .`、`git commit`、`git push`，PR 会自动更新。

**2. 临时要修紧急 Bug 怎么办？**
如果你正在开发功能，突然要修一个紧急 Bug：

```bash
# 1. 先暂存当前的修改
git stash
# 2. 切回主分支拉取最新代码，并创建修复分支
git checkout main
git pull origin main
git checkout -b hotfix/urgent-bug
# 3. 修完 Bug 后，正常走 add -> commit -> push -> PR 流程
# 4. 修完后，切回原来的功能分支，恢复之前的修改
git checkout feature/login
git stash pop
```

