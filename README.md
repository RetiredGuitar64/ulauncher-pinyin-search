# Ulauncher Pinyin File Search

一个面向 Linux 本地文件的 Ulauncher 扩展。它像 Listary 一样按文件名快速查找，支持：

- 英文模糊匹配：`mprn` 可以匹配 `MyProjectReleaseNotes.md`
- 中文原名匹配：`我的笔记`
- 连续全拼匹配：`wodebiji` 可以匹配 `我的笔记.md`
- 拼音首字母匹配：`wdbj` 也可以匹配 `我的笔记.md`
- 文件和目录结果，按回车使用桌面默认程序打开

## 工作方式

扩展启动搜索后，会在后台调用 [`fd`](https://github.com/sharkdp/fd) 扫描配置的目录，并将文件名、全拼和拼音首字母保存为内存索引。SQLite 缓存位于：

```text
${XDG_CACHE_HOME:-~/.cache}/ulauncher-pinyin-search/
```

后续启动会先加载缓存，因此不必等待磁盘扫描。索引到达刷新周期后，会在下一次查询时后台更新。索引尚未建好时，英文查询直接使用 `fd` 返回结果。

拼音转换优先使用 ICU 的 `uconv`，不依赖 pip 包。缺少 `uconv` 时会启用一个覆盖常见文件名用字的简化后备表；为了得到完整的汉字覆盖，建议安装 ICU。

## Arch Linux 依赖

```bash
sudo pacman -S ulauncher fd icu
```

- `ulauncher`：主程序
- `fd`：强烈建议，用于快速并行扫描；缺少时会回退到 Python `os.walk`
- `icu`：强烈建议，用于完整的汉字转拼音

插件没有需要单独安装的 Python 包。

## 从 GitHub 安装

1. 把本仓库推送到 GitHub，默认分支保留为 `master`。
2. 打开 **Ulauncher Preferences → Extensions → Add extension**。
3. 粘贴仓库 URL，例如 `https://github.com/你的用户名/ulauncher-pinyin-search`。
4. 安装完成后，在 Ulauncher 中输入 `f wodebiji`。

仓库根目录中的 `versions.json` 已将 Ulauncher Extension API v2 指向 `master`，可以直接通过 GitHub URL 安装。

## 配置

在 Ulauncher 的扩展设置中可以修改：

- 触发关键字（默认 `f`）
- 搜索根目录（默认 `~`，每行一个目录）
- `fd` 排除 glob（默认排除 `.git`、`node_modules`、`.cache` 等）
- 是否包含隐藏文件、是否遵循 `.gitignore`
- 只搜文件、只搜目录或两者都搜
- 是否跟随符号链接
- 最大显示结果、最短查询长度
- 索引刷新周期、最大索引条目数

修改影响索引的设置后，新索引会自动在后台构建。默认最多索引 200,000 个条目，避免意外扫描极大的挂载点。

## 本地开发与调试

官方文档要求扩展位于 `~/.local/share/ulauncher/extensions/`。开发时可以建立软链接：

```bash
mkdir -p ~/.local/share/ulauncher/extensions
ln -s "$PWD" ~/.local/share/ulauncher/extensions/ulauncher-pinyin-search
ulauncher --no-extensions --dev -v
```

如果目标路径已经存在，请先自行确认并移走旧目录，不要直接覆盖。运行测试：

```bash
python3 -m unittest discover -v
```

## 已知边界

- Ulauncher 扩展只能响应“关键字 + 空格”形式的查询，不能接管 Ulauncher 的全局默认搜索框。
- 多音字使用 ICU 给出的常用读音；当前不会为每个多音字建立所有读音组合。
- 索引按文件名搜索，不读取文件内容。
- `fd` 默认遵循 ignore 文件；可在扩展设置中关闭。

## License

[MIT](LICENSE)
