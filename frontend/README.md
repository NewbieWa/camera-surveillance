# 前端服务安装和运行说明

## 安装依赖

```bash
yarn install
```

## 运行服务

```bash
# 使用npx serve运行前端服务
npx serve -s .
```

或者使用Python内置服务器：

```bash
# Python 3
python -m http.server 3000
```

## 目录结构

```
frontend/
├── index.html          # 主页面
├── demo.html           # 示例页面
├── style.css           # 样式文件
├── package.json        # 依赖配置
├── yarn.lock           # yarn锁定文件
├── img/                # 图片资源
├── js/                 # 第三方JavaScript库
├── jssdk/              # MCS8 JavaScript SDK
└── doc/                # 文档目录
```

## 访问地址

- 主页面: http://localhost:3000/index.html
- 示例页面: http://localhost:3000/demo.html