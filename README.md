# 点云地图转换工具 GUI

一个集成了 LAS→PCD 转换、点云分割、批量处理功能的可视化工具。

![版本](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.6+-green)
![PyQt5](https://img.shields.io/badge/PyQt5-5.0+-orange)

## 🎯 功能特性

### ✨ 核心功能

1. **LAS → PCD 转换**
   - RGB 点云转换 (las2pcd)
   - 强度点云转换 (las2pcd_intensity)
   - 自动读取 LAS 元数据
   - 智能原点处理

2. **点云分割**
   - 按网格分割大型点云
   - 可配置网格大小
   - 体素降采样
   - 自动生成元数据

3. **PCD 增强**
   - Gamma 校正
   - 提高对比度

4. **批量处理**
   - 批量 LAS→PCD 转换
   - 进度实时显示

## 🚀 快速开始

### 启动方式

#### 方式1: 双击启动
```bash
# 双击以下任一文件
点云转换工具.desktop
pointcloud_converter_gui.py
```

#### 方式2: 命令行
```bash
python3 pointcloud_converter_gui.py
```

#### 方式3: 添加到桌面
```bash
cp 点云转换工具.desktop ~/Desktop/
chmod +x ~/Desktop/点云转换工具.desktop
```

## 📚 文档

- **快速使用**: [QUICKSTART.md](QUICKSTART.md)
- **更新说明**: [UPDATE.md](UPDATE.md)

## 🔧 依赖工具

### 必需
- Python 3.6+
- PyQt5
- pyyaml
- lasinfo (liblas-bin)

### 编译后的工具
- `/home/luo/map_ws/las2pcd/build/las2pcd`
- `/home/luo/map_ws/las2pcd/build/las2pcd_intensity`
- `/home/luo/map_ws/las2pcd/build/pcd_enhancer`
- `/home/luo/map_ws/pointcloud_divider-master/build/pointcloud_divider`

### 安装依赖
```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt5 python3-yaml liblas-bin

# 或使用 pip
pip3 install PyQt5 pyyaml
```

## 📖 原点坐标说明

### LAS 文件元数据

选择 LAS 文件后,工具会自动显示:
- 📁 文件信息
- 🔖 LAS 版本
- 📍 点数量
- 📐 **原点偏移 (Offset)** ← 重要!
- 📏 边界范围
- 🔬 坐标精度

### 两种转换模式

| 模式 | 默认原点 | 输出格式 |
|------|---------|----------|
| **RGB 点云** | LAS 文件头 Offset | PointXYZRGB |
| **强度点云** | 第一个点坐标 | PointXYZI |

### 原点处理逻辑

```python
# RGB 模式
PCD坐标 = LAS坐标 - header.GetOffset()

# 强度模式
PCD坐标 = LAS坐标 - 第一个点坐标

# 自定义模式
PCD坐标 = LAS坐标 - (x0, y0, z0)
```

## 🎨 界面预览

### 选项卡

1. **LAS → PCD**: LAS 转 PCD 转换
2. **点云分割**: 大文件网格分割
3. **PCD 增强**: RGB 点云增强
4. **批量处理**: 批量文件转换
5. **一键流程**: 完整处理流程 (开发中)

## 📊 典型工作流程

### 场景1: 单文件转换
```
LAS文件 → [LAS→PCD] → PCD文件
```

### 场景2: 大文件处理
```
大LAS文件 → [LAS→PCD] → 大PCD文件 → [点云分割] → 多个小PCD文件
```

### 场景3: 批量转换
```
多个LAS文件 → [批量处理] → 多个PCD文件
```

### 场景4: 完整流程
```
LAS → PCD → 分割 → 增强 (可选)
```

## ⚙️ 配置参数

### LAS → PCD
- **转换类型**: RGB / 强度
- **原点模式**: 默认 / 自定义
- **坐标偏移**: x0, y0, z0

### 点云分割
- **网格大小**: 默认 20m × 20m
- **降采样**: 默认 0.2m (可设为0跳过)
- **合并模式**: 是否合并为单文件

### PCD 增强
- **Gamma 值**: 固定 0.8
- **仅支持**: RGB 点云

## 🐛 常见问题

### Q: 看不到 LAS 文件信息?
```bash
# 安装 liblas
sudo apt-get install liblas-bin
```

### Q: RGB 模式和强度模式区别?
- **RGB**: 包含颜色信息 (PointXYZRGB)
- **强度**: 只有激光强度 (PointXYZI)

### Q: 转换后坐标很小?
正常! 这是局部坐标系,已减去原点偏移。

### Q: 如何知道使用的原点?
查看转换日志:
```
the origin coordinate is x0 = 500000.00, y0 = 4000000.00, z0 = 0.00
```

## 📝 技术细节

### 架构
```
GUI (PyQt5)
  ├── ConversionWorker (QThread) - 后台转换线程
  └── PointCloudConverterGUI (QMainWindow) - 主窗口

调用外部工具:
  ├── lasinfo - 读取 LAS 元数据
  ├── las2pcd - LAS→PCD (RGB)
  ├── las2pcd_intensity - LAS→PCD (强度)
  ├── pcd_enhancer - PCD 增强
  └── pointcloud_divider - 点云分割
```

### 文件结构
```
/home/luo/map_ws/
├── pointcloud_converter_gui.py  # 主程序
├── 点云转换工具.desktop          # 启动器
├── README.md                     # 本文件
├── QUICKSTART.md                 # 快速指南
├── UPDATE.md                     # 更新说明
├── las2pcd/                      # LAS转PCD工具
│   └── build/
│       ├── las2pcd
│       ├── las2pcd_intensity
│       └── pcd_enhancer
├── libLAS-master/                # libLAS库
└── pointcloud_divider-master/    # 点云分割工具
    └── build/
        └── pointcloud_divider
```

## 🎓 学习资源

### LAS 格式
- [ASPRS LAS Specification](https://www.asprs.org/divisions-committees/lidar-division/laser-las-file-format-exchange-activities)
- [libLAS Documentation](https://liblas.org/)

### PCD 格式
- [PCL Point Cloud Data Format](https://pointclouds.org/documentation/tutorials/pcd_file_format.html)

## 📄 许可证

根据原始工具的许可证使用。

## 🙏 致谢

整合了以下优秀工具:
- [las2pcd](https://github.com/tmcdonell/las2pcd) - LAS to PCD converter
- [libLAS](https://liblas.org/) - LAS format library
- [pointcloud_divider](https://github.com/MapIV/pointcloud_divider) - Point cloud division tool

## 📞 联系方式

如有问题,请查看:
- [QUICKSTART.md](QUICKSTART.md) - 快速使用指南
- [UPDATE.md](UPDATE.md) - 详细更新说明

---

**版本**: 2.0  
**更新日期**: 2025-12-03  
**状态**: ✅ 稳定版
