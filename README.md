# ⭐ Star 星星走起 动动发财手点点 ⭐
Weirdhost & 自动续期 & 多账号版

### 注册地址：https://hub.weirdhost.xyz

### ✅ 需要添加的 Secrets

> 进入仓库：**Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 示例值 | 说明 |
|:--|:--|:--|
| `WEIRDHOST_COOKIE_1` | `我的账号-----remember_web_59ba36addc2b2f940CCCC=XXXXXXXXXXX` | 账号1 的 Cookie（支持备注前缀） |
| `WEIRDHOST_COOKIE_2` | `我的账号-----remember_web_59ba36addc2b2f940CCCC=XXXXXXXXXXX` | 账号2 的 Cookie（支持备注前缀） |
| `WEIRDHOST_COOKIE_3` | `我的账号-----remember_web_59ba36addc2b2f940CCCC=XXXXXXXXXXX` | 账号3 的 Cookie（支持备注前缀） |
| ... | `...` | 最多支持5个账号（1~5） |
| `REPO_TOKEN` | `ghp_xxxxxxxxxxxx` | GitHub Personal Access Token（用于自动更新Cookie） |
| `TG_BOT_TOKEN` | `123456789:ABC-XYZ...` | Telegram Bot Token（用于通知） |
| `TG_CHAT_ID` | `123456789` | Telegram Chat ID（用于通知） |

> **注意**：如果不需要自动更新Cookie，可以不设置`REPO_TOKEN`；如果不需要Telegram通知，可以不设置`TG_BOT_TOKEN`和`TG_CHAT_ID`。

---

### 📌 Cookie 格式说明

每个账号的 Cookie 需要以 **`备注-----remember_web_xxx=yyy`** 的格式填写到对应的 `WEIRDHOST_COOKIE_N` 中：

- `备注`：自定义标识（可留空，但建议保留便于识别）
- `-----`：分隔符（固定）
- `remember_web_xxx=yyy`：从浏览器获取的完整 Cookie 键值对

**示例**：
```
我的主账号-----remember_web_59ba36addc2b2f940CCCC=abcdef1234567890
```

如果不需要备注，也可以直接填写纯 Cookie 格式：
```
remember_web_59ba36addc2b2f940CCCC=abcdef1234567890
```

> 如何获取 Cookie？  
> 登录 Weirdhost 后，在浏览器开发者工具中查看 `Application` → `Cookies`，找到以 `remember_web_` 开头的 Cookie，复制其完整的 `名称=值` 即可。

![示例输出](img/hub.weirdhost.xyz.Cookie.png)

---
