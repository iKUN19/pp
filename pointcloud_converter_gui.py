#!/usr/bin/env python3
"""
点云地图转换工具 - 图形界面版本
整合 las2pcd、pointcloud_divider 和 pcd_enhancer 功能
"""

import sys
import os
import subprocess
import yaml
import re
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QGroupBox, QProgressBar, QMessageBox, QTabWidget, QCheckBox,
    QListWidget, QSpinBox, QDoubleSpinBox, QComboBox, QGridLayout,
    QRadioButton, QButtonGroup, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor


class ConversionWorker(QThread):
    """后台转换线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, task_type, params):
        super().__init__()
        self.task_type = task_type
        self.params = params

    def run(self):
        try:
            if self.task_type == 'las2pcd':
                self.convert_las_to_pcd()
            elif self.task_type == 'divide':
                self.divide_pointcloud()
            elif self.task_type == 'enhance':
                self.enhance_pcd()
            elif self.task_type == 'batch':
                self.batch_process()
            elif self.task_type == 'pipeline':
                self.pipeline_process()
        except Exception as e:
            self.finished.emit(False, f"处理失败: {str(e)}")

    def convert_las_to_pcd(self):
        """LAS转PCD"""
        input_file = self.params['input_file']
        output_file = self.params['output_file']
        conversion_type = self.params['conversion_type']

        # 选择转换程序
        if conversion_type == 'rgb':
            cmd = ['/home/luo/map_ws/las2pcd/build/las2pcd']
        else:
            cmd = ['/home/luo/map_ws/las2pcd/build/las2pcd_intensity']

        cmd.extend([input_file, output_file])

        self.progress.emit(f"执行命令: {' '.join(cmd)}")
        self.progress.emit("开始转换...")

        # 执行转换
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # 实时输出
        for line in process.stdout:
            self.progress.emit(line.strip())

        process.wait()

        if process.returncode == 0:
            # 检查输出文件
            if os.path.exists(output_file):
                size = os.path.getsize(output_file) / (1024 * 1024)  # MB
                self.finished.emit(True, f"转换成功！输出文件: {output_file} ({size:.2f} MB)")
            else:
                self.finished.emit(False, "转换完成但未找到输出文件")
        else:
            stderr = process.stderr.read()
            self.finished.emit(False, f"转换失败: {stderr}")

    def divide_pointcloud(self):
        """点云分割"""
        input_files = self.params['input_files']
        output_dir = self.params['output_dir']
        prefix = self.params['prefix']
        grid_size_x = self.params['grid_size_x']
        grid_size_y = self.params['grid_size_y']
        leaf_size = self.params['leaf_size']
        merge_pcds = self.params['merge_pcds']

        # 确保输出目录以斜杠结尾
        if not output_dir.endswith('/'):
            output_dir = output_dir + '/'

        # 创建临时配置文件
        config_file = '/tmp/pointcloud_divider_temp.yaml'
        config = {
            'pointcloud_divider': {
                'grid_size_x': grid_size_x,
                'grid_size_y': grid_size_y,
                'leaf_size': leaf_size,
                'merge_pcds': merge_pcds,
                'use_large_grid': False
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        self.progress.emit(f"配置参数:")
        self.progress.emit(f"  输出目录: {output_dir}")
        self.progress.emit(f"  文件前缀: {prefix}")
        self.progress.emit(f"  网格大小: {grid_size_x}m x {grid_size_y}m")
        self.progress.emit(f"  降采样: {'是 ('+str(leaf_size)+'m)' if leaf_size > 0 else '否'}")
        self.progress.emit(f"  合并模式: {'是' if merge_pcds else '否'}")
        self.progress.emit("")

        # 构建命令
        cmd = [
            '/home/luo/map_ws/pointcloud_divider-master/build/pointcloud_divider',
            str(len(input_files))
        ]
        cmd.extend(input_files)
        cmd.extend([output_dir, prefix, config_file])

        self.progress.emit(f"处理 {len(input_files)} 个文件...")
        self.progress.emit("")

        # 执行分割
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # 实时输出
        for line in process.stdout:
            self.progress.emit(line.strip())

        process.wait()

        if process.returncode == 0:
            # 统计输出文件
            output_files = list(Path(output_dir).glob('*.pcd'))
            metadata_file = os.path.join(output_dir, f'{prefix}_metadata.yaml')

            msg = f"分割成功！\n"
            msg += f"输出目录: {output_dir}\n"
            msg += f"生成文件: {len(output_files)} 个PCD文件"

            if os.path.exists(metadata_file):
                msg += f"\n元数据文件: {prefix}_metadata.yaml"

            self.finished.emit(True, msg)
        else:
            stderr = process.stderr.read()
            self.finished.emit(False, f"分割失败: {stderr}")

    def enhance_pcd(self):
        """PCD增强"""
        input_file = self.params['input_file']
        output_file = self.params['output_file']

        cmd = [
            '/home/luo/map_ws/las2pcd/build/pcd_enhancer',
            input_file,
            output_file
        ]

        self.progress.emit(f"执行命令: {' '.join(cmd)}")
        self.progress.emit("开始增强处理...")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        for line in process.stdout:
            self.progress.emit(line.strip())

        process.wait()

        if process.returncode == 0:
            self.finished.emit(True, f"增强成功！输出文件: {output_file}")
        else:
            stderr = process.stderr.read()
            self.finished.emit(False, f"增强失败: {stderr}")

    def batch_process(self):
        """批量处理"""
        tasks = self.params['tasks']
        total = len(tasks)
        success_count = 0
        fail_count = 0

        for idx, task in enumerate(tasks):
            self.progress.emit(f"\n{'='*60}")
            self.progress.emit(f"[{idx+1}/{total}] 处理: {task['input_file']}")
            self.progress.emit('='*60)

            # 根据任务类型执行
            if task['type'] == 'las2pcd':
                cmd = [task['executable'], task['input_file'], task['output_file']]
                if 'offsets' in task:
                    cmd.extend(task['offsets'])
            elif task['type'] == 'enhance':
                cmd = [task['executable'], task['input_file'], task['output_file']]
            else:
                continue

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if process.returncode == 0:
                success_count += 1
                self.progress.emit(f"✓ 成功")
            else:
                fail_count += 1
                self.progress.emit(f"✗ 失败: {process.stderr}")

        self.progress.emit(f"\n{'='*60}")
        self.progress.emit(f"批量处理完成:")
        self.progress.emit(f"  总数: {total}")
        self.progress.emit(f"  成功: {success_count}")
        self.progress.emit(f"  失败: {fail_count}")
        self.progress.emit('='*60)

        self.finished.emit(True, f"批量处理完成\n成功: {success_count} / 失败: {fail_count}")

    def pipeline_process(self):
        """一键流程处理: LAS→PCD→分割→(可选)增强"""
        input_file = self.params['input_file']
        output_dir = self.params['output_dir']
        conversion_type = self.params['conversion_type']
        grid_size = self.params['grid_size']
        leaf_size = self.params['leaf_size']
        enhance = self.params['enhance']

        # 确保输出目录以斜杠结尾
        if not output_dir.endswith('/'):
            output_dir = output_dir + '/'

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 阶段1: LAS → PCD
        self.progress.emit("\n" + "="*60)
        self.progress.emit("阶段 1/3: LAS → PCD 转换")
        self.progress.emit("="*60)

        base_name = os.path.basename(input_file).rsplit('.', 1)[0]
        temp_pcd = os.path.join(output_dir, base_name + '_temp.pcd')

        # 选择转换程序
        if conversion_type == 'rgb':
            las2pcd_cmd = ['/home/luo/map_ws/las2pcd/build/las2pcd']
        else:
            las2pcd_cmd = ['/home/luo/map_ws/las2pcd/build/las2pcd_intensity']

        las2pcd_cmd.extend([input_file, temp_pcd])
        self.progress.emit(f"执行命令: {' '.join(las2pcd_cmd)}")

        process = subprocess.run(
            las2pcd_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if process.returncode != 0:
            self.finished.emit(False, f"LAS转PCD失败: {process.stderr}")
            return

        self.progress.emit("✓ LAS转PCD完成")

        # 阶段2: 点云分割
        self.progress.emit("\n" + "="*60)
        self.progress.emit("阶段 2/3: 点云分割")
        self.progress.emit("="*60)

        # 创建临时配置文件
        config_file = '/tmp/pointcloud_divider_pipeline.yaml'
        config = {
            'pointcloud_divider': {
                'grid_size_x': grid_size,
                'grid_size_y': grid_size,
                'leaf_size': leaf_size,
                'merge_pcds': False,
                'use_large_grid': False
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        divide_cmd = [
            '/home/luo/map_ws/pointcloud_divider-master/build/pointcloud_divider',
            '1',
            temp_pcd,
            output_dir,
            'pointcloud_map',
            config_file
        ]

        self.progress.emit(f"网格大小: {grid_size}m x {grid_size}m")
        self.progress.emit(f"降采样: {'是 ('+str(leaf_size)+'m)' if leaf_size > 0 else '否'}")

        process = subprocess.run(
            divide_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if process.returncode != 0:
            self.finished.emit(False, f"点云分割失败: {process.stderr}")
            return

        self.progress.emit("✓ 点云分割完成")

        # 删除临时PCD文件
        if os.path.exists(temp_pcd):
            os.remove(temp_pcd)
            self.progress.emit(f"✓ 已清理临时文件")

        # 阶段3: (可选) PCD增强
        if enhance:
            self.progress.emit("\n" + "="*60)
            self.progress.emit("阶段 3/3: PCD增强处理")
            self.progress.emit("="*60)

            # 找到所有分割后的PCD文件
            pcd_files = list(Path(output_dir).glob('pointcloud_map_*.pcd'))
            total = len(pcd_files)
            self.progress.emit(f"找到 {total} 个PCD文件需要增强")

            success_count = 0
            for idx, pcd_file in enumerate(pcd_files):
                pcd_path = str(pcd_file)
                enhanced_path = pcd_path.rsplit('.', 1)[0] + '_enhanced.pcd'

                enhance_cmd = [
                    '/home/luo/map_ws/las2pcd/build/pcd_enhancer',
                    pcd_path,
                    enhanced_path
                ]

                process = subprocess.run(
                    enhance_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if process.returncode == 0:
                    # 用增强后的文件替换原文件
                    os.replace(enhanced_path, pcd_path)
                    success_count += 1
                    self.progress.emit(f"[{idx+1}/{total}] ✓ {os.path.basename(pcd_path)}")
                else:
                    self.progress.emit(f"[{idx+1}/{total}] ✗ {os.path.basename(pcd_path)} - {process.stderr}")

            self.progress.emit(f"✓ 增强处理完成: 成功 {success_count}/{total}")
        else:
            self.progress.emit("\n阶段 3/3: 跳过增强处理")

        # 统计最终结果
        output_files = list(Path(output_dir).glob('pointcloud_map_*.pcd'))
        metadata_file = os.path.join(output_dir, 'pointcloud_map_metadata.yaml')

        self.progress.emit("\n" + "="*60)
        self.progress.emit("一键流程处理完成!")
        self.progress.emit("="*60)
        self.progress.emit(f"输出目录: {output_dir}")
        self.progress.emit(f"生成文件: {len(output_files)} 个PCD文件")
        if os.path.exists(metadata_file):
            self.progress.emit(f"元数据文件: pointcloud_map_metadata.yaml")

        self.finished.emit(True, f"一键流程完成！\n输出目录: {output_dir}\n生成 {len(output_files)} 个PCD文件")


class PointCloudConverterGUI(QMainWindow):
    """点云转换工具主窗口"""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("点云地图转换工具")
        self.setGeometry(100, 100, 1200, 800)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 标题
        title = QLabel("点云地图转换工具 (LAS → PCD → 分割)")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # 创建选项卡
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 选项卡1: LAS转PCD
        self.las2pcd_tab = self.create_las2pcd_tab()
        self.tabs.addTab(self.las2pcd_tab, "LAS → PCD")

        # 选项卡2: 点云分割
        self.divide_tab = self.create_divide_tab()
        self.tabs.addTab(self.divide_tab, "点云分割")

        # 选项卡3: PCD增强
        self.enhance_tab = self.create_enhance_tab()
        self.tabs.addTab(self.enhance_tab, "PCD增强")

        # 选项卡4: 批量处理
        self.batch_tab = self.create_batch_tab()
        self.tabs.addTab(self.batch_tab, "批量处理")

        # 选项卡5: 一键流程
        self.pipeline_tab = self.create_pipeline_tab()
        self.tabs.addTab(self.pipeline_tab, "一键流程")

        # 状态栏
        self.statusBar().showMessage("就绪")

    def create_las2pcd_tab(self):
        """创建LAS转PCD选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 输入文件
        input_group = QGroupBox("1. 选择输入文件")
        input_layout = QHBoxLayout()
        input_group.setLayout(input_layout)

        self.las_input = QLineEdit()
        self.las_input.setPlaceholderText("选择 LAS 文件...")
        self.las_input.textChanged.connect(self.on_las_file_changed)
        input_layout.addWidget(self.las_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_las_file)
        input_layout.addWidget(browse_btn)

        layout.addWidget(input_group)

        # LAS文件信息
        info_group = QGroupBox("2. LAS 文件信息")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)

        self.las_info_text = QTextEdit()
        self.las_info_text.setReadOnly(True)
        self.las_info_text.setMaximumHeight(180)
        self.las_info_text.setPlaceholderText("选择LAS文件后将显示元数据信息...")
        info_layout.addWidget(self.las_info_text)

        layout.addWidget(info_group)

        # 输出文件
        output_group = QGroupBox("3. 输出文件")
        output_layout = QVBoxLayout()
        output_group.setLayout(output_layout)

        # 命名方式选择
        naming_layout = QHBoxLayout()
        naming_layout.addWidget(QLabel("命名方式:"))
        self.naming_mode_group = QButtonGroup()

        self.auto_naming_radio = QRadioButton("自动命名 (与输入文件同名)")
        self.auto_naming_radio.setChecked(True)
        self.auto_naming_radio.toggled.connect(self.on_naming_mode_changed)
        self.naming_mode_group.addButton(self.auto_naming_radio, 0)
        naming_layout.addWidget(self.auto_naming_radio)

        self.custom_naming_radio = QRadioButton("自定义文件名")
        self.custom_naming_radio.toggled.connect(self.on_naming_mode_changed)
        self.naming_mode_group.addButton(self.custom_naming_radio, 1)
        naming_layout.addWidget(self.custom_naming_radio)

        naming_layout.addStretch()
        output_layout.addLayout(naming_layout)

        # 输出目录选择
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("输出目录:"))
        self.pcd_output_dir = QLineEdit()
        self.pcd_output_dir.setPlaceholderText("选择输出目录...")
        self.pcd_output_dir.textChanged.connect(self.on_pcd_output_dir_changed)
        dir_layout.addWidget(self.pcd_output_dir)

        browse_dir_btn = QPushButton("浏览...")
        browse_dir_btn.clicked.connect(self.browse_pcd_output_dir)
        dir_layout.addWidget(browse_dir_btn)
        output_layout.addLayout(dir_layout)

        # 自定义文件名输入
        custom_name_layout = QHBoxLayout()
        custom_name_layout.addWidget(QLabel("文件名:"))
        self.pcd_custom_name = QLineEdit()
        self.pcd_custom_name.setPlaceholderText("输入自定义文件名...")
        self.pcd_custom_name.setEnabled(False)
        self.pcd_custom_name.textChanged.connect(self.on_pcd_output_dir_changed)
        custom_name_layout.addWidget(self.pcd_custom_name)

        pcd_suffix_label = QLabel(".pcd")
        pcd_suffix_label.setStyleSheet("font-weight: bold; color: #666;")
        custom_name_layout.addWidget(pcd_suffix_label)

        output_layout.addLayout(custom_name_layout)

        # 输出文件完整路径 (只读显示)
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("完整路径:"))
        self.pcd_output = QLineEdit()
        self.pcd_output.setPlaceholderText("输出文件完整路径...")
        self.pcd_output.setReadOnly(True)
        self.pcd_output.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        file_layout.addWidget(self.pcd_output)
        output_layout.addLayout(file_layout)

        layout.addWidget(output_group)

        # 转换选项
        options_group = QGroupBox("4. 转换选项")
        options_layout = QGridLayout()
        options_group.setLayout(options_layout)

        # 转换类型
        options_layout.addWidget(QLabel("转换类型:"), 0, 0)
        self.conversion_type = QComboBox()
        self.conversion_type.addItems(['RGB点云 (las2pcd)', '强度点云 (las2pcd_intensity)'])
        options_layout.addWidget(self.conversion_type, 0, 1, 1, 3)


        layout.addWidget(options_group)

        # 转换按钮
        convert_btn = QPushButton("开始转换")
        convert_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 14px; padding: 10px; }")
        convert_btn.clicked.connect(self.start_las2pcd_conversion)
        layout.addWidget(convert_btn)

        # 进度条
        self.las2pcd_progress = QProgressBar()
        self.las2pcd_progress.setVisible(False)
        self.las2pcd_progress.setTextVisible(False)  # 不显示文字
        layout.addWidget(self.las2pcd_progress)

        # 日志
        log_group = QGroupBox("转换日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.las2pcd_log = QTextEdit()
        self.las2pcd_log.setReadOnly(True)
        log_layout.addWidget(self.las2pcd_log)

        layout.addWidget(log_group)

        return widget

    def create_divide_tab(self):
        """创建点云分割选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 输入文件列表
        input_group = QGroupBox("1. 输入点云文件")
        input_layout = QVBoxLayout()
        input_group.setLayout(input_layout)

        btn_layout = QHBoxLayout()
        add_file_btn = QPushButton("添加文件")
        add_file_btn.clicked.connect(self.add_pcd_files)
        btn_layout.addWidget(add_file_btn)

        remove_file_btn = QPushButton("移除选中")
        remove_file_btn.clicked.connect(self.remove_pcd_files)
        btn_layout.addWidget(remove_file_btn)

        clear_file_btn = QPushButton("清空列表")
        clear_file_btn.clicked.connect(self.clear_pcd_files)
        btn_layout.addWidget(clear_file_btn)

        input_layout.addLayout(btn_layout)

        self.pcd_file_list = QListWidget()
        input_layout.addWidget(self.pcd_file_list)

        layout.addWidget(input_group)

        # 输出配置
        output_group = QGroupBox("2. 输出配置")
        output_layout = QGridLayout()
        output_group.setLayout(output_layout)

        output_layout.addWidget(QLabel("输出目录:"), 0, 0)
        self.divide_output_dir = QLineEdit()
        output_layout.addWidget(self.divide_output_dir, 0, 1)

        browse_dir_btn = QPushButton("浏览...")
        browse_dir_btn.clicked.connect(self.browse_divide_output_dir)
        output_layout.addWidget(browse_dir_btn, 0, 2)

        output_layout.addWidget(QLabel("文件前缀:"), 1, 0)
        self.divide_prefix = QLineEdit()
        self.divide_prefix.setText("pointcloud_map")
        output_layout.addWidget(self.divide_prefix, 1, 1, 1, 2)

        layout.addWidget(output_group)

        # 分割参数
        params_group = QGroupBox("3. 分割参数")
        params_layout = QGridLayout()
        params_group.setLayout(params_layout)

        params_layout.addWidget(QLabel("网格大小 X (米):"), 0, 0)
        self.grid_size_x = QSpinBox()
        self.grid_size_x.setRange(1, 1000)
        self.grid_size_x.setValue(20)
        params_layout.addWidget(self.grid_size_x, 0, 1)

        params_layout.addWidget(QLabel("网格大小 Y (米):"), 0, 2)
        self.grid_size_y = QSpinBox()
        self.grid_size_y.setRange(1, 1000)
        self.grid_size_y.setValue(20)
        params_layout.addWidget(self.grid_size_y, 0, 3)

        params_layout.addWidget(QLabel("降采样叶子大小 (米):"), 1, 0)
        self.leaf_size = QDoubleSpinBox()
        self.leaf_size.setRange(0, 10)
        self.leaf_size.setDecimals(2)
        self.leaf_size.setSingleStep(0.1)
        self.leaf_size.setValue(0.2)
        params_layout.addWidget(self.leaf_size, 1, 1)

        info_label = QLabel("(设为0跳过降采样)")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        params_layout.addWidget(info_label, 1, 2, 1, 2)

        self.merge_pcds_check = QCheckBox("合并为单个文件 (否则按网格分割)")
        params_layout.addWidget(self.merge_pcds_check, 2, 0, 1, 4)

        layout.addWidget(params_group)

        # 分割按钮
        divide_btn = QPushButton("开始分割")
        divide_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-size: 14px; padding: 10px; }")
        divide_btn.clicked.connect(self.start_divide)
        layout.addWidget(divide_btn)

        # 进度条
        self.divide_progress = QProgressBar()
        self.divide_progress.setVisible(False)
        self.divide_progress.setTextVisible(False)  # 不显示文字
        layout.addWidget(self.divide_progress)

        # 日志
        log_group = QGroupBox("分割日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.divide_log = QTextEdit()
        self.divide_log.setReadOnly(True)
        log_layout.addWidget(self.divide_log)

        layout.addWidget(log_group)

        return widget

    def create_enhance_tab(self):
        """创建PCD增强选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 输入文件
        input_group = QGroupBox("1. 选择输入文件")
        input_layout = QHBoxLayout()
        input_group.setLayout(input_layout)

        self.enhance_input = QLineEdit()
        self.enhance_input.setPlaceholderText("选择 PCD 文件...")
        input_layout.addWidget(self.enhance_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_enhance_input)
        input_layout.addWidget(browse_btn)

        layout.addWidget(input_group)

        # 输出文件
        output_group = QGroupBox("2. 输出文件")
        output_layout = QHBoxLayout()
        output_group.setLayout(output_layout)

        self.enhance_output = QLineEdit()
        self.enhance_output.setPlaceholderText("自动生成或手动指定...")
        output_layout.addWidget(self.enhance_output)

        browse_out_btn = QPushButton("保存为...")
        browse_out_btn.clicked.connect(self.save_enhance_output)
        output_layout.addWidget(browse_out_btn)

        layout.addWidget(output_group)

        # 说明
        info_group = QGroupBox("增强说明")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)

        info_text = QLabel(
            "PCD增强功能将对RGB点云进行Gamma校正 (gamma=0.8)\n"
            "这将提高点云的对比度和可视化效果\n"
            "仅适用于RGB格式的点云文件"
        )
        info_text.setStyleSheet("color: #555; padding: 10px;")
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # 增强按钮
        enhance_btn = QPushButton("开始增强")
        enhance_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-size: 14px; padding: 10px; }")
        enhance_btn.clicked.connect(self.start_enhance)
        layout.addWidget(enhance_btn)

        # 进度条
        self.enhance_progress = QProgressBar()
        self.enhance_progress.setVisible(False)
        self.enhance_progress.setTextVisible(False)  # 不显示文字
        layout.addWidget(self.enhance_progress)

        # 日志
        log_group = QGroupBox("增强日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.enhance_log = QTextEdit()
        self.enhance_log.setReadOnly(True)
        log_layout.addWidget(self.enhance_log)

        layout.addWidget(log_group)

        return widget

    def create_batch_tab(self):
        """创建批量处理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 说明文本
        info_label = QLabel("批量处理可以为每个文件单独设置输出文件名")
        info_label.setStyleSheet("color: #555; font-style: italic; padding: 5px;")
        layout.addWidget(info_label)

        # 文件操作按钮
        btn_layout = QHBoxLayout()
        add_las_btn = QPushButton("添加LAS文件")
        add_las_btn.clicked.connect(self.add_batch_las_files)
        btn_layout.addWidget(add_las_btn)

        remove_las_btn = QPushButton("移除选中")
        remove_las_btn.clicked.connect(self.remove_batch_las_files)
        btn_layout.addWidget(remove_las_btn)

        clear_las_btn = QPushButton("清空列表")
        clear_las_btn.clicked.connect(self.clear_batch_las_files)
        btn_layout.addWidget(clear_las_btn)

        btn_layout.addStretch()

        # 转换类型
        btn_layout.addWidget(QLabel("转换类型:"))
        self.batch_conversion_type = QComboBox()
        self.batch_conversion_type.addItems(['RGB点云', '强度点云'])
        btn_layout.addWidget(self.batch_conversion_type)

        layout.addLayout(btn_layout)

        # 文件列表表格
        files_group = QGroupBox("文件列表 (可编辑输出文件名)")
        files_layout = QVBoxLayout()
        files_group.setLayout(files_layout)

        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(3)
        self.batch_table.setHorizontalHeaderLabels(['输入文件', '输出文件名', '输出路径预览'])

        # 设置列宽
        header = self.batch_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 输入文件自动拉伸
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # 输出文件名可调整
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 输出路径预览自动拉伸
        self.batch_table.setColumnWidth(1, 200)

        # 连接单元格改变信号
        self.batch_table.cellChanged.connect(self.on_batch_table_cell_changed)

        files_layout.addWidget(self.batch_table)

        layout.addWidget(files_group)

        # 输出目录配置
        output_group = QGroupBox("输出目录")
        output_layout = QHBoxLayout()
        output_group.setLayout(output_layout)

        output_layout.addWidget(QLabel("输出目录:"))
        self.batch_output_dir = QLineEdit()
        self.batch_output_dir.setPlaceholderText("选择输出目录...")
        self.batch_output_dir.textChanged.connect(self.on_batch_output_dir_changed)
        output_layout.addWidget(self.batch_output_dir)

        batch_browse_btn = QPushButton("浏览...")
        batch_browse_btn.clicked.connect(self.browse_batch_output_dir)
        output_layout.addWidget(batch_browse_btn)

        layout.addWidget(output_group)

        # 快速命名工具
        naming_group = QGroupBox("快速命名工具")
        naming_layout = QHBoxLayout()
        naming_group.setLayout(naming_layout)

        naming_layout.addWidget(QLabel("批量添加前缀:"))
        self.batch_prefix_input = QLineEdit()
        self.batch_prefix_input.setPlaceholderText("例如: converted_")
        naming_layout.addWidget(self.batch_prefix_input)

        apply_prefix_btn = QPushButton("应用到所有文件")
        apply_prefix_btn.clicked.connect(self.apply_batch_prefix)
        naming_layout.addWidget(apply_prefix_btn)

        naming_layout.addWidget(QLabel("  |  批量添加后缀:"))
        self.batch_suffix_input = QLineEdit()
        self.batch_suffix_input.setPlaceholderText("例如: _processed")
        naming_layout.addWidget(self.batch_suffix_input)

        apply_suffix_btn = QPushButton("应用到所有文件")
        apply_suffix_btn.clicked.connect(self.apply_batch_suffix)
        naming_layout.addWidget(apply_suffix_btn)

        reset_naming_btn = QPushButton("重置为原文件名")
        reset_naming_btn.clicked.connect(self.reset_batch_naming)
        naming_layout.addWidget(reset_naming_btn)

        layout.addWidget(naming_group)

        # 批量转换按钮
        batch_convert_btn = QPushButton("开始批量转换")
        batch_convert_btn.setStyleSheet("QPushButton { background-color: #9C27B0; color: white; font-size: 14px; padding: 8px; }")
        batch_convert_btn.clicked.connect(self.start_batch_conversion)
        layout.addWidget(batch_convert_btn)

        # 进度条
        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        self.batch_progress.setTextVisible(False)
        layout.addWidget(self.batch_progress)

        # 日志
        log_group = QGroupBox("批量处理日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.batch_log = QTextEdit()
        self.batch_log.setReadOnly(True)
        log_layout.addWidget(self.batch_log)

        layout.addWidget(log_group)

        return widget

    def create_pipeline_tab(self):
        """创建一键流程选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 流程说明
        info_group = QGroupBox("一键处理流程")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)

        info_text = QLabel(
            "自动执行完整的点云处理流程:\n\n"
            "1. LAS → PCD 转换\n"
            "2. PCD 点云分割\n"
            "3. (可选) PCD 增强处理\n\n"
            "适合需要完整处理流程的场景"
        )
        info_text.setStyleSheet("color: #555; padding: 10px; font-size: 12px;")
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # 输入LAS文件
        input_group = QGroupBox("1. 输入LAS文件")
        input_layout = QHBoxLayout()
        input_group.setLayout(input_layout)

        self.pipeline_input = QLineEdit()
        input_layout.addWidget(self.pipeline_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_pipeline_input)
        input_layout.addWidget(browse_btn)

        layout.addWidget(input_group)

        # 输出目录
        output_group = QGroupBox("2. 输出目录")
        output_layout = QHBoxLayout()
        output_group.setLayout(output_layout)

        self.pipeline_output = QLineEdit()
        output_layout.addWidget(self.pipeline_output)

        browse_out_btn = QPushButton("浏览...")
        browse_out_btn.clicked.connect(self.browse_pipeline_output)
        output_layout.addWidget(browse_out_btn)

        layout.addWidget(output_group)

        # 处理选项
        options_group = QGroupBox("3. 处理选项")
        options_layout = QGridLayout()
        options_group.setLayout(options_layout)

        options_layout.addWidget(QLabel("转换类型:"), 0, 0)
        self.pipeline_type = QComboBox()
        self.pipeline_type.addItems(['RGB点云', '强度点云'])
        options_layout.addWidget(self.pipeline_type, 0, 1)

        self.pipeline_enhance = QCheckBox("执行增强处理")
        options_layout.addWidget(self.pipeline_enhance, 0, 2)

        options_layout.addWidget(QLabel("网格大小:"), 1, 0)
        self.pipeline_grid = QSpinBox()
        self.pipeline_grid.setRange(1, 1000)
        self.pipeline_grid.setValue(20)
        self.pipeline_grid.setSuffix(" m")
        options_layout.addWidget(self.pipeline_grid, 1, 1)

        options_layout.addWidget(QLabel("降采样:"), 1, 2)
        self.pipeline_leaf = QDoubleSpinBox()
        self.pipeline_leaf.setRange(0, 10)
        self.pipeline_leaf.setDecimals(2)
        self.pipeline_leaf.setValue(0.2)
        self.pipeline_leaf.setSuffix(" m")
        options_layout.addWidget(self.pipeline_leaf, 1, 3)

        layout.addWidget(options_group)

        # 开始按钮
        start_btn = QPushButton("开始一键处理")
        start_btn.setStyleSheet("QPushButton { background-color: #E91E63; color: white; font-size: 16px; padding: 12px; }")
        start_btn.clicked.connect(self.start_pipeline)
        layout.addWidget(start_btn)

        # 进度条
        self.pipeline_progress = QProgressBar()
        self.pipeline_progress.setVisible(False)
        self.pipeline_progress.setTextVisible(False)  # 不显示文字
        layout.addWidget(self.pipeline_progress)

        # 日志
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.pipeline_log = QTextEdit()
        self.pipeline_log.setReadOnly(True)
        log_layout.addWidget(self.pipeline_log)

        layout.addWidget(log_group)

        return widget

    # ==================== 辅助函数 ====================

    def get_las_metadata(self, las_file):
        """读取LAS文件元数据 - 优先使用pdal,备用lasinfo"""

        # 方法1: 尝试使用 pdal (更可靠,JSON格式)
        metadata = self.get_las_metadata_pdal(las_file)
        if metadata and len(metadata) > 0:
            return metadata

        # 方法2: 回退到 lasinfo
        metadata = self.get_las_metadata_lasinfo(las_file)
        if metadata and len(metadata) > 0:
            return metadata

        return None

    def get_las_metadata_pdal(self, las_file):
        """使用 pdal 读取 LAS 元数据"""
        try:
            result = subprocess.run(
                ['pdal', 'info', '--metadata', las_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30
            )

            if result.returncode != 0:
                return None

            # 解析 JSON 输出
            data = json.loads(result.stdout)

            # 提取 metadata 部分
            if 'metadata' not in data:
                return None

            meta = data['metadata']
            metadata = {}

            # 提取各项信息
            if 'count' in meta:
                metadata['point_count'] = int(meta['count'])

            # 提取版本
            if 'major_version' in meta and 'minor_version' in meta:
                metadata['version'] = f"{meta['major_version']}.{meta['minor_version']}"

            # 提取边界
            if 'minx' in meta:
                metadata['min_x'] = float(meta['minx'])
                metadata['min_y'] = float(meta['miny'])
                metadata['min_z'] = float(meta['minz'])

            if 'maxx' in meta:
                metadata['max_x'] = float(meta['maxx'])
                metadata['max_y'] = float(meta['maxy'])
                metadata['max_z'] = float(meta['maxz'])

            # 提取 Offset (重要!)
            if 'offset_x' in meta:
                metadata['offset_x'] = float(meta['offset_x'])
                metadata['offset_y'] = float(meta['offset_y'])
                metadata['offset_z'] = float(meta['offset_z'])

            # 提取 Scale
            if 'scale_x' in meta:
                metadata['scale_x'] = float(meta['scale_x'])
                metadata['scale_y'] = float(meta['scale_y'])
                metadata['scale_z'] = float(meta['scale_z'])

            # 提取其他信息
            if 'software_id' in meta:
                metadata['software'] = meta['software_id']

            if 'system_id' in meta:
                metadata['system'] = meta['system_id']

            metadata['source'] = 'pdal'
            return metadata

        except subprocess.TimeoutExpired:
            print(f"pdal 读取超时: {las_file}")
            return None
        except json.JSONDecodeError as e:
            print(f"pdal JSON 解析失败: {e}")
            return None
        except Exception as e:
            print(f"pdal 读取失败: {e}")
            return None

    def get_las_metadata_lasinfo(self, las_file):
        """使用 lasinfo 读取 LAS 元数据 (备用方案)"""
        try:
            result = subprocess.run(
                ['lasinfo', las_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            output = result.stdout

            # 解析关键信息
            metadata = {}

            # 提取点数量
            match = re.search(r'Number of Point Records:\s+(\d+)', output, re.IGNORECASE)
            if match:
                metadata['point_count'] = int(match.group(1))

            # 提取版本
            match = re.search(r'Version:\s+([\d.]+)', output, re.IGNORECASE)
            if match:
                metadata['version'] = match.group(1)

            # 提取边界 - 注意格式: "Min X Y Z:   635619.85 848899.70 406.59"
            match = re.search(r'Min X Y Z:\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', output, re.IGNORECASE)
            if match:
                metadata['min_x'] = float(match.group(1))
                metadata['min_y'] = float(match.group(2))
                metadata['min_z'] = float(match.group(3))

            match = re.search(r'Max X Y Z:\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', output, re.IGNORECASE)
            if match:
                metadata['max_x'] = float(match.group(1))
                metadata['max_y'] = float(match.group(2))
                metadata['max_z'] = float(match.group(3))

            # 提取Offset (原点坐标) - 注意格式: "Offset X Y Z:  -0.00 -0.00 -0.00"
            match = re.search(r'Offset X Y Z:\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', output, re.IGNORECASE)
            if match:
                metadata['offset_x'] = float(match.group(1))
                metadata['offset_y'] = float(match.group(2))
                metadata['offset_z'] = float(match.group(3))

            # 提取Scale - 注意格式: "Scale Factor X Y Z:  0.01 0.01 0.01"
            match = re.search(r'Scale Factor X Y Z:\s+([\d.e-]+)\s+([\d.e-]+)\s+([\d.e-]+)', output, re.IGNORECASE)
            if match:
                metadata['scale_x'] = float(match.group(1))
                metadata['scale_y'] = float(match.group(2))
                metadata['scale_z'] = float(match.group(3))

            metadata['source'] = 'lasinfo'
            return metadata

        except subprocess.TimeoutExpired:
            print(f"lasinfo 读取超时: {las_file}")
            return None
        except Exception as e:
            print(f"lasinfo 读取失败: {e}")
            return None

    def on_las_file_changed(self, file_path):
        """当LAS文件路径改变时"""
        if not file_path or not os.path.exists(file_path):
            self.las_info_text.clear()
            return

        # 更新输出文件路径
        self.on_pcd_output_dir_changed()

        # 读取元数据
        metadata = self.get_las_metadata(file_path)

        if metadata and len(metadata) > 0:
            info_lines = []
            info_lines.append(f"📁 文件: {os.path.basename(file_path)}")

            try:
                file_size = os.path.getsize(file_path) / (1024*1024)
                info_lines.append(f"📊 文件大小: {file_size:.2f} MB")
            except:
                pass

            # 显示数据来源
            if 'source' in metadata:
                info_lines.append(f"🔧 读取工具: {metadata['source']}")

            if 'version' in metadata:
                info_lines.append(f"\n🔖 LAS版本: {metadata['version']}")

            if 'point_count' in metadata:
                info_lines.append(f"📍 点数量: {metadata['point_count']:,}")

            # 显示软件信息
            if 'software' in metadata:
                info_lines.append(f"💻 生成软件: {metadata['software']}")

            if 'offset_x' in metadata:
                info_lines.append(f"\n📐 原点偏移 (Offset):")
                info_lines.append(f"   X: {metadata['offset_x']:.12f}")
                info_lines.append(f"   Y: {metadata['offset_y']:.12f}")
                info_lines.append(f"   Z: {metadata['offset_z']:.12f}")
                info_lines.append(f"   ⚠️  RGB模式将使用此偏移作为默认原点")

            if 'min_x' in metadata and 'max_x' in metadata:
                info_lines.append(f"\n📏 边界范围:")
                info_lines.append(f"   X: [{metadata['min_x']:.2f}, {metadata['max_x']:.2f}]")
                info_lines.append(f"   Y: [{metadata['min_y']:.2f}, {metadata['max_y']:.2f}]")
                info_lines.append(f"   Z: [{metadata['min_z']:.2f}, {metadata['max_z']:.2f}]")

            if 'scale_x' in metadata:
                info_lines.append(f"\n🔬 精度 (Scale):")
                info_lines.append(f"   X/Y/Z: {metadata['scale_x']:.10f}")

            self.las_info_text.setPlainText('\n'.join(info_lines))
        else:
            # 即使无法读取元数据,也显示基本信息
            info_lines = []
            info_lines.append(f"📁 文件: {os.path.basename(file_path)}")

            try:
                file_size = os.path.getsize(file_path) / (1024*1024)
                info_lines.append(f"📊 文件大小: {file_size:.2f} MB")
            except:
                pass

            info_lines.append(f"\n⚠️  无法读取详细的LAS文件元数据")
            info_lines.append(f"\n可能原因:")
            info_lines.append(f"  • pdal 或 lasinfo 工具未正确安装")
            info_lines.append(f"  • LAS 文件格式不正确")
            info_lines.append(f"  • 文件权限问题")
            info_lines.append(f"\n解决方法:")
            info_lines.append(f"  1. 检查 pdal: which pdal")
            info_lines.append(f"  2. 安装 pdal: sudo apt-get install pdal")
            info_lines.append(f"  3. 手动测试: pdal info --metadata {file_path}")

            self.las_info_text.setPlainText('\n'.join(info_lines))

    def browse_las_file(self):
        """浏览LAS文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择LAS文件",
            "",
            "LAS Files (*.las);;All Files (*)"
        )
        if file_path:
            self.las_input.setText(file_path)
            # 自动设置输出目录为输入文件所在目录
            if not self.pcd_output_dir.text():
                input_dir = os.path.dirname(file_path)
                self.pcd_output_dir.setText(input_dir)

    def browse_pcd_output_dir(self):
        """浏览PCD输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.pcd_output_dir.setText(directory)

    def on_naming_mode_changed(self):
        """命名方式改变时的处理"""
        is_custom = self.custom_naming_radio.isChecked()
        self.pcd_custom_name.setEnabled(is_custom)

        if is_custom:
            # 切换到自定义模式，清空自定义文件名以便用户输入
            if not self.pcd_custom_name.text():
                self.pcd_custom_name.setFocus()

        # 更新输出路径
        self.on_pcd_output_dir_changed()

    def on_pcd_output_dir_changed(self):
        """当输出目录或文件名改变时，更新输出文件路径"""
        output_dir = self.pcd_output_dir.text()
        input_file = self.las_input.text()

        if not output_dir:
            self.pcd_output.clear()
            return

        # 根据命名模式生成文件名
        if self.auto_naming_radio.isChecked():
            # 自动命名：使用输入文件名
            if input_file and os.path.exists(input_file):
                base_name = os.path.basename(input_file).rsplit('.', 1)[0]
                output_file = os.path.join(output_dir, base_name + '.pcd')
                self.pcd_output.setText(output_file)
            else:
                self.pcd_output.setText(output_dir + "/")
        else:
            # 自定义命名：使用用户输入的文件名
            custom_name = self.pcd_custom_name.text().strip()
            if custom_name:
                # 移除可能的.pcd后缀
                if custom_name.endswith('.pcd'):
                    custom_name = custom_name[:-4]
                output_file = os.path.join(output_dir, custom_name + '.pcd')
                self.pcd_output.setText(output_file)
            else:
                self.pcd_output.setText(output_dir + "/")

    def add_pcd_files(self):
        """添加PCD文件到分割列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择PCD文件",
            "",
            "PCD Files (*.pcd);;All Files (*)"
        )
        for file_path in files:
            if not self.is_file_in_list(self.pcd_file_list, file_path):
                self.pcd_file_list.addItem(file_path)

    def remove_pcd_files(self):
        """移除选中的PCD文件"""
        for item in self.pcd_file_list.selectedItems():
            self.pcd_file_list.takeItem(self.pcd_file_list.row(item))

    def clear_pcd_files(self):
        """清空PCD文件列表"""
        self.pcd_file_list.clear()

    def browse_divide_output_dir(self):
        """浏览分割输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.divide_output_dir.setText(directory)

    def browse_enhance_input(self):
        """浏览增强输入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择PCD文件",
            "",
            "PCD Files (*.pcd);;All Files (*)"
        )
        if file_path:
            self.enhance_input.setText(file_path)
            # 自动生成输出文件名
            if not self.enhance_output.text():
                base = file_path.rsplit('.', 1)[0]
                output = base + '_enhanced.pcd'
                self.enhance_output.setText(output)

    def save_enhance_output(self):
        """保存增强输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存增强PCD文件",
            "",
            "PCD Files (*.pcd);;All Files (*)"
        )
        if file_path:
            self.enhance_output.setText(file_path)

    def add_batch_las_files(self):
        """添加批量LAS文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择LAS文件",
            "",
            "LAS Files (*.las);;All Files (*)"
        )

        if not files:
            return

        # 暂时断开信号以避免重复更新
        self.batch_table.cellChanged.disconnect(self.on_batch_table_cell_changed)

        for file_path in files:
            # 检查是否已存在
            exists = False
            for row in range(self.batch_table.rowCount()):
                if self.batch_table.item(row, 0).text() == file_path:
                    exists = True
                    break

            if not exists:
                # 添加新行
                row_position = self.batch_table.rowCount()
                self.batch_table.insertRow(row_position)

                # 列0: 输入文件路径 (只读)
                input_item = QTableWidgetItem(file_path)
                input_item.setFlags(input_item.flags() & ~Qt.ItemIsEditable)  # 设为只读
                input_item.setToolTip(file_path)
                self.batch_table.setItem(row_position, 0, input_item)

                # 列1: 输出文件名 (可编辑)
                base_name = os.path.basename(file_path).rsplit('.', 1)[0]
                output_name = base_name + '.pcd'
                output_name_item = QTableWidgetItem(output_name)
                self.batch_table.setItem(row_position, 1, output_name_item)

                # 列2: 输出路径预览 (只读)
                preview_item = QTableWidgetItem("")
                preview_item.setFlags(preview_item.flags() & ~Qt.ItemIsEditable)
                preview_item.setForeground(Qt.gray)
                self.batch_table.setItem(row_position, 2, preview_item)

        # 重新连接信号
        self.batch_table.cellChanged.connect(self.on_batch_table_cell_changed)

        # 更新所有输出路径预览
        self.update_all_output_previews()

    def remove_batch_las_files(self):
        """移除选中的批量LAS文件"""
        selected_rows = set()
        for item in self.batch_table.selectedItems():
            selected_rows.add(item.row())

        # 从大到小删除，避免索引变化
        for row in sorted(selected_rows, reverse=True):
            self.batch_table.removeRow(row)

    def clear_batch_las_files(self):
        """清空批量LAS文件"""
        self.batch_table.setRowCount(0)

    def on_batch_table_cell_changed(self, row, column):
        """表格单元格改变时的处理"""
        if column == 1:  # 输出文件名列
            # 更新该行的输出路径预览
            self.update_output_preview(row)

    def on_batch_output_dir_changed(self):
        """输出目录改变时更新所有预览"""
        self.update_all_output_previews()

    def update_output_preview(self, row):
        """更新指定行的输出路径预览"""
        output_dir = self.batch_output_dir.text()
        if not output_dir:
            self.batch_table.item(row, 2).setText("请先选择输出目录")
            return

        output_name_item = self.batch_table.item(row, 1)
        if output_name_item:
            output_name = output_name_item.text().strip()
            if not output_name:
                output_name = "未命名.pcd"

            # 确保有.pcd后缀
            if not output_name.endswith('.pcd'):
                output_name += '.pcd'
                # 更新输出文件名
                self.batch_table.cellChanged.disconnect(self.on_batch_table_cell_changed)
                output_name_item.setText(output_name)
                self.batch_table.cellChanged.connect(self.on_batch_table_cell_changed)

            output_path = os.path.join(output_dir, output_name)
            self.batch_table.item(row, 2).setText(output_path)
            self.batch_table.item(row, 2).setToolTip(output_path)

    def update_all_output_previews(self):
        """更新所有行的输出路径预览"""
        for row in range(self.batch_table.rowCount()):
            self.update_output_preview(row)

    def apply_batch_prefix(self):
        """应用批量前缀到所有文件"""
        prefix = self.batch_prefix_input.text().strip()
        if not prefix:
            QMessageBox.warning(self, "提示", "请输入前缀")
            return

        # 暂时断开信号
        self.batch_table.cellChanged.disconnect(self.on_batch_table_cell_changed)

        for row in range(self.batch_table.rowCount()):
            output_name_item = self.batch_table.item(row, 1)
            current_name = output_name_item.text().strip()

            # 移除.pcd后缀
            if current_name.endswith('.pcd'):
                current_name = current_name[:-4]

            # 如果已经有前缀，先移除旧前缀（简单判断：如果开头有下划线前的部分）
            # 这里使用原始文件名作为基础
            input_path = self.batch_table.item(row, 0).text()
            base_name = os.path.basename(input_path).rsplit('.', 1)[0]

            new_name = prefix + base_name + '.pcd'
            output_name_item.setText(new_name)

        # 重新连接信号
        self.batch_table.cellChanged.connect(self.on_batch_table_cell_changed)

        # 更新所有预览
        self.update_all_output_previews()

    def apply_batch_suffix(self):
        """应用批量后缀到所有文件"""
        suffix = self.batch_suffix_input.text().strip()
        if not suffix:
            QMessageBox.warning(self, "提示", "请输入后缀")
            return

        # 暂时断开信号
        self.batch_table.cellChanged.disconnect(self.on_batch_table_cell_changed)

        for row in range(self.batch_table.rowCount()):
            output_name_item = self.batch_table.item(row, 1)
            current_name = output_name_item.text().strip()

            # 移除.pcd后缀
            if current_name.endswith('.pcd'):
                current_name = current_name[:-4]

            # 使用原始文件名作为基础
            input_path = self.batch_table.item(row, 0).text()
            base_name = os.path.basename(input_path).rsplit('.', 1)[0]

            new_name = base_name + suffix + '.pcd'
            output_name_item.setText(new_name)

        # 重新连接信号
        self.batch_table.cellChanged.connect(self.on_batch_table_cell_changed)

        # 更新所有预览
        self.update_all_output_previews()

    def reset_batch_naming(self):
        """重置所有文件名为原文件名"""
        # 暂时断开信号
        self.batch_table.cellChanged.disconnect(self.on_batch_table_cell_changed)

        for row in range(self.batch_table.rowCount()):
            input_path = self.batch_table.item(row, 0).text()
            base_name = os.path.basename(input_path).rsplit('.', 1)[0]
            output_name = base_name + '.pcd'
            self.batch_table.item(row, 1).setText(output_name)

        # 重新连接信号
        self.batch_table.cellChanged.connect(self.on_batch_table_cell_changed)

        # 更新所有预览
        self.update_all_output_previews()

    def browse_batch_output_dir(self):
        """浏览批量输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.batch_output_dir.setText(directory)

    def browse_pipeline_input(self):
        """浏览流程输入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择LAS文件",
            "",
            "LAS Files (*.las);;All Files (*)"
        )
        if file_path:
            self.pipeline_input.setText(file_path)

    def browse_pipeline_output(self):
        """浏览流程输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self.pipeline_output.setText(directory)

    def is_file_in_list(self, list_widget, file_path):
        """检查文件是否已在列表中"""
        for i in range(list_widget.count()):
            if list_widget.item(i).text() == file_path:
                return True
        return False

    # ==================== 处理函数 ====================

    def start_las2pcd_conversion(self):
        """开始LAS转PCD转换"""
        input_file = self.las_input.text()
        output_file = self.pcd_output.text()

        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "错误", "请选择有效的输入文件")
            return

        if not output_file:
            QMessageBox.warning(self, "错误", "请指定输出文件")
            return

        # 获取转换类型
        conversion_type = 'rgb' if self.conversion_type.currentIndex() == 0 else 'intensity'

        # 准备参数
        params = {
            'input_file': input_file,
            'output_file': output_file,
            'conversion_type': conversion_type
        }

        # 清空日志
        self.las2pcd_log.clear()
        self.las2pcd_progress.setVisible(True)
        self.las2pcd_progress.setRange(0, 0)  # 无限滚动模式

        # 启动转换线程
        self.worker = ConversionWorker('las2pcd', params)
        self.worker.progress.connect(self.las2pcd_log.append)
        self.worker.finished.connect(self.on_las2pcd_finished)
        self.worker.start()

        self.statusBar().showMessage("正在转换...")

    def on_las2pcd_finished(self, success, message):
        """LAS转PCD完成回调"""
        self.las2pcd_progress.setVisible(False)
        self.statusBar().showMessage("就绪")

        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", message)

    def start_divide(self):
        """开始点云分割"""
        # 获取输入文件列表
        input_files = []
        for i in range(self.pcd_file_list.count()):
            input_files.append(self.pcd_file_list.item(i).text())

        if not input_files:
            QMessageBox.warning(self, "错误", "请添加至少一个PCD文件")
            return

        output_dir = self.divide_output_dir.text()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请指定输出目录")
            return

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        prefix = self.divide_prefix.text() or "pointcloud_map"

        # 准备参数
        params = {
            'input_files': input_files,
            'output_dir': output_dir,
            'prefix': prefix,
            'grid_size_x': self.grid_size_x.value(),
            'grid_size_y': self.grid_size_y.value(),
            'leaf_size': self.leaf_size.value(),
            'merge_pcds': self.merge_pcds_check.isChecked()
        }

        # 清空日志
        self.divide_log.clear()
        self.divide_progress.setVisible(True)
        self.divide_progress.setRange(0, 0)  # 无限滚动模式

        # 启动分割线程
        self.worker = ConversionWorker('divide', params)
        self.worker.progress.connect(self.divide_log.append)
        self.worker.finished.connect(self.on_divide_finished)
        self.worker.start()

        self.statusBar().showMessage("正在分割...")

    def on_divide_finished(self, success, message):
        """点云分割完成回调"""
        self.divide_progress.setVisible(False)
        self.statusBar().showMessage("就绪")

        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", message)

    def start_enhance(self):
        """开始PCD增强"""
        input_file = self.enhance_input.text()
        output_file = self.enhance_output.text()

        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "错误", "请选择有效的输入文件")
            return

        if not output_file:
            QMessageBox.warning(self, "错误", "请指定输出文件")
            return

        params = {
            'input_file': input_file,
            'output_file': output_file
        }

        # 清空日志
        self.enhance_log.clear()
        self.enhance_progress.setVisible(True)
        self.enhance_progress.setRange(0, 0)  # 无限滚动模式

        # 启动增强线程
        self.worker = ConversionWorker('enhance', params)
        self.worker.progress.connect(self.enhance_log.append)
        self.worker.finished.connect(self.on_enhance_finished)
        self.worker.start()

        self.statusBar().showMessage("正在增强...")

    def on_enhance_finished(self, success, message):
        """增强完成回调"""
        self.enhance_progress.setVisible(False)
        self.statusBar().showMessage("就绪")

        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", message)

    def start_batch_conversion(self):
        """开始批量转换"""
        # 检查表格是否有文件
        if self.batch_table.rowCount() == 0:
            QMessageBox.warning(self, "错误", "请添加至少一个LAS文件")
            return

        output_dir = self.batch_output_dir.text()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请指定输出目录")
            return

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 获取转换类型
        conversion_type = 'rgb' if self.batch_conversion_type.currentIndex() == 0 else 'intensity'
        executable = '/home/luo/map_ws/las2pcd/build/las2pcd' if conversion_type == 'rgb' else '/home/luo/map_ws/las2pcd/build/las2pcd_intensity'

        # 从表格中读取任务列表
        tasks = []
        for row in range(self.batch_table.rowCount()):
            input_file = self.batch_table.item(row, 0).text()
            output_name = self.batch_table.item(row, 1).text().strip()

            # 确保输出文件名有.pcd后缀
            if not output_name.endswith('.pcd'):
                output_name += '.pcd'

            output_file = os.path.join(output_dir, output_name)

            tasks.append({
                'type': 'las2pcd',
                'input_file': input_file,
                'output_file': output_file,
                'executable': executable
            })

        params = {'tasks': tasks}

        # 清空日志
        self.batch_log.clear()
        self.batch_progress.setVisible(True)
        self.batch_progress.setRange(0, 0)  # 无限滚动模式

        # 启动批量处理
        self.worker = ConversionWorker('batch', params)
        self.worker.progress.connect(self.batch_log.append)
        self.worker.finished.connect(self.on_batch_finished)
        self.worker.start()

        self.statusBar().showMessage("正在批量处理...")

    def on_batch_finished(self, success, message):
        """批量处理完成回调"""
        self.batch_progress.setVisible(False)
        self.statusBar().showMessage("就绪")

        QMessageBox.information(self, "批量处理完成", message)

    def start_pipeline(self):
        """开始一键流程"""
        input_file = self.pipeline_input.text()
        output_dir = self.pipeline_output.text()

        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "错误", "请选择有效的LAS文件")
            return

        if not output_dir:
            QMessageBox.warning(self, "错误", "请指定输出目录")
            return

        # 获取参数
        conversion_type = 'rgb' if self.pipeline_type.currentIndex() == 0 else 'intensity'
        grid_size = self.pipeline_grid.value()
        leaf_size = self.pipeline_leaf.value()
        enhance = self.pipeline_enhance.isChecked()

        # 准备参数
        params = {
            'input_file': input_file,
            'output_dir': output_dir,
            'conversion_type': conversion_type,
            'grid_size': grid_size,
            'leaf_size': leaf_size,
            'enhance': enhance
        }

        # 清空日志
        self.pipeline_log.clear()
        self.pipeline_progress.setVisible(True)
        self.pipeline_progress.setRange(0, 0)  # 无限滚动模式

        # 启动一键流程线程
        self.worker = ConversionWorker('pipeline', params)
        self.worker.progress.connect(self.on_pipeline_progress)
        self.worker.finished.connect(self.on_pipeline_finished)
        self.worker.start()

        self.statusBar().showMessage("正在执行一键流程...")

    def on_pipeline_progress(self, message):
        """一键流程进度消息"""
        self.pipeline_log.append(message)
        # 自动滚动到底部
        self.pipeline_log.moveCursor(QTextCursor.End)

    def on_pipeline_finished(self, success, message):
        """一键流程完成回调"""
        self.pipeline_progress.setVisible(False)
        self.statusBar().showMessage("就绪")

        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", message)


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 创建主窗口
    window = PointCloudConverterGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
