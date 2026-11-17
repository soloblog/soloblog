# 在 Sealos 上部署和托管 Soloblog

Soloblog 是一个免费、开源、为个人打造的博客和个人网站。此模板在 Sealos 上运行一个 Soloblog 容器，带有保存全部数据的持久卷和 HTTPS 地址。

![Soloblog 截图](https://raw.githubusercontent.com/labring-actions/templates/kb-0.9/template/soloblog/website-screenshot.webp)

## 关于托管 Soloblog

Soloblog 把文章（Markdown 文件）、SQLite 数据库、图片和设置都保存在一个文件夹里，这里挂载在 `/data`。不需要单独的数据库服务器。它只运行一个副本，因此模板固定为一个副本。

## 常见用途

- **个人博客**：在简洁的编辑器中写作，有 35 种配色可选。
- **个人网站**：用区块搭建主页、作品集或图书介绍页。
- **电子报**：读者可以通过电子邮件订阅，或在 Mastodon 上关注。
- **会员专属文章**：免费或付费，通过电子邮件登录。

## 部署之后

打开应用地址。首次设置会要求输入设置令牌（setup token）：在 Sealos 中打开应用详情，再打开日志，复制标有 `[setup]` 的行中的令牌。然后设置密码，并保存它给出的恢复密钥。

## 依赖

- **Soloblog**：`ghcr.io/soloblog/soloblog`
- **持久存储**：`/data`，保存文章、图片、数据库和设置
- **网络入口**：Service、HTTPS Ingress 和 Sealos App 资源

### 相关文档

- [Soloblog 用户指南（英文）](https://github.com/soloblog/soloblog/blob/master/docs/guide/README.md)
- [Soloblog 部署指南（英文）](https://github.com/soloblog/soloblog/blob/master/docs/DEPLOYMENT.md)
- [Soloblog 源代码](https://github.com/soloblog/soloblog)
- [Sealos 文档](https://sealos.io/docs)
