# INSIGHTFACE 人脸考勤系统部署方案

## 一、系统概述

### 1.1 项目背景
为现有不锈钢网带跟单系统（调度中心端口5003、容器中心端口5002）增加本地化人脸考勤功能，采用INSIGHTFACE开源框架实现高精度人脸识别。

### 1.2 技术选型

| 组件 | 技术方案 | 说明 |
|------|---------|------|
| **人脸识别框架** | INSIGHTFACE v0.7.3+ | ArcFace算法，商业级精度 |
| **推理引擎** | ONNXRuntime GPU/CPU | 支持CUDA加速 |
| **模型** | buffalo_l | 高精度人脸检测+识别 |
| **后端** | Flask | 复用现有框架 |
| **数据库** | SQLite | 复用现有face_checkin.db |
| **前端** | 升级现有TensorFlow.js方案 | 或新增Python服务端API |

### 1.3 性能指标

| 指标 | CPU模式 | GPU模式 |
|------|--------|---------|
| 单次识别延迟 | 200-500ms | 50-100ms |
| 支持人员规模 | 100-500人 | 1000+人 |
| 识别准确率 | 99.5%+ | 99.7%+ |
| GPU显存需求 | 无 | 4GB+ |

---

## 二、硬件要求

### 2.1 最低配置（CPU模式）
- CPU: Intel i5 / AMD Ryzen 5 及以上
- 内存: 8GB
- 存储: 2GB可用空间

### 2.2 推荐配置（GPU模式）
- GPU: NVIDIA GTX 1060 6GB 或更高
- CPU: Intel i7 / AMD Ryzen 7 及以上
- 内存: 16GB
- CUDA: 11.8 或 12.x
- cuDNN: 8.x

---

## 三、依赖安装

### 3.1 Python环境
```bash
# 推荐使用Anaconda创建独立环境
conda create -n insightface python=3.9
conda activate insightface

# 或使用虚拟环境
python -m venv venv_insightface
.\venv_insightface\Scripts\activate
```

### 3.2 核心依赖
```bash
# CPU版本
pip install insightface onnxruntime opencv-python-headless numpy pillow onnx scikit-image scipy scikit-learn requests tqdm albumentations prettytable matplotlib cython easydict

# GPU版本（推荐）
pip install insightface onnxruntime-gpu opencv-python-headless numpy pillow onnx scikit-image scipy scikit-learn requests tqdm albumentations prettytable matplotlib cython easydict
```

### 3.3 版本兼容性

| 组件 | 推荐版本 | 注意事项 |
|------|---------|---------|
| Python | 3.8-3.10 | 3.11+需确认兼容性 |
| numpy | 1.21-1.24 | **避免2.x**，会导致np.int报错 |
| onnxruntime-gpu | 1.16.0 | 需与CUDA版本匹配 |
| opencv-python | 4.9+ | 服务器环境用headless版本 |

---

## 四、模型下载与配置

### 4.1 模型文件

| 模型 | 文件大小 | 用途 |
|------|---------|------|
| buffalo_l | ~160MB | 高精度人脸检测+识别（**推荐**） |
| buffalo_m | ~90MB | 中等精度，平衡性能 |
| buffalo_s | ~50MB | 快速版本，适合移动端 |

### 4.2 模型下载

**下载地址**：
```
https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
```

**存放路径**：
- Windows: `%USERPROFILE%\.insightface\models\buffalo_l\`
- 或项目目录: `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\models\buffalo_l\`

**自动下载**（首次运行时会自动下载）：
```python
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))
```

### 4.3 模型文件结构
```
buffalo_l/
├── 2d106det/          # 106点关键点检测
│   └── 2d106det.onnx
├── det_10g.onnx       # 人脸检测模型（10GFLOPS）
├── w600k_r50.onnx     # 人脸识别模型（50层ResNet）
├── genderage.onnx     # 性别年龄预测
└── buffalo_l.json     # 模型配置文件
```

---

## 五、系统架构

### 5.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户端（浏览器）                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  摄像头捕获  │→│  人脸检测   │→│  特征上传   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP POST /api/face/recognize
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Flask API 服务 (5009)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ /api/enroll │  │/api/recogn  │  │/api/checkin │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │            │
│  ┌──────▼────────────────▼────────────────▼──────┐     │
│  │           INSIGHTFACE Engine                 │     │
│  │  ┌─────────────────────────────────────┐   │     │
│  │  │  buffalo_l 模型                      │   │     │
│  │  │  - 人脸检测 (RetinaFace)            │   │     │
│  │  │  - 特征提取 (ArcFace)              │   │     │
│  │  └─────────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────┘     │
└──────────────────────────┬──────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  SQLite DB  │    │ 容器中心     │    │ 调度中心    │
│  face.db   │    │  (5002)     │    │  (5003)     │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 5.2 API接口设计

#### 5.2.1 人脸注册
```
POST /api/face/enroll
Content-Type: application/json

Request:
{
  "name": "张三",
  "photo": "base64编码的照片数据"
}

Response:
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "name": "张三",
    "embedding_size": 512,
    "registered_at": "2024-01-15 10:30:00"
  }
}
```

#### 5.2.2 人脸识别
```
POST /api/face/recognize
Content-Type: application/json

Request:
{
  "photo": "base64编码的照片数据",
  "threshold": 0.5  // 可选，相似度阈值，默认0.5
}

Response:
{
  "code": 0,
  "message": "识别成功",
  "data": {
    "name": "张三",
    "similarity": 0.856,
    "confidence": "high",  // high/medium/low
    "bbox": [x1, y1, x2, y2]
  }
}
```

#### 5.2.3 人脸考勤
```
POST /api/face/checkin
Content-Type: application/json

Request:
{
  "name": "张三",
  "similarity": 0.856,
  "photo_path": "attendance/zhangsan_1705289400000.jpg"
}

Response:
{
  "code": 0,
  "message": "签到成功",
  "data": {
    "checkin_time": "2024-01-15 10:30:00",
    "cooldown_remaining": 0
  }
}
```

---

## 六、核心代码实现

### 6.1 INSIGHTFACE 初始化模块

```python
# face_engine.py
import os
import logging
from pathlib import Path
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

class FaceEngine:
    def __init__(self, model_name='buffalo_l', ctx_id=0, det_size=(640, 640)):
        self.model_name = model_name
        self.ctx_id = ctx_id
        self.det_size = det_size
        self.app = None
        self._initialized = False

    def initialize(self):
        """初始化INSIGHTFACE模型"""
        try:
            logger.info(f"正在初始化 {self.model_name} 模型...")
            self.app = FaceAnalysis(name=self.model_name)
            self.app.prepare(ctx_id=self.ctx_id, det_size=self.det_size)
            self._initialized = True
            logger.info(f"INSIGHTFACE 模型初始化成功 (ctx_id={self.ctx_id})")
            return True
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            return False

    def detect_faces(self, img):
        """检测人脸"""
        if not self._initialized:
            return []
        try:
            faces = self.app.get(img)
            return faces
        except Exception as e:
            logger.error(f"人脸检测失败: {e}")
            return []

    def get_embedding(self, img, face=None):
        """获取人脸特征向量"""
        if not self._initialized:
            return None
        try:
            if face is None:
                faces = self.app.get(img)
                if not faces:
                    return None
                face = faces[0]
            return face.normed_embedding.tolist()
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            return None
```

### 6.2 人脸识别服务

```python
# face_recognition_service.py
import numpy as np
from scipy.spatial.distance import cosine
from face_engine import FaceEngine

class FaceRecognitionService:
    def __init__(self, threshold=0.5):
        self.engine = FaceEngine()
        self.engine.initialize()
        self.threshold = threshold
        self.embeddings_db = {}  # name -> embedding

    def register(self, name, embedding):
        """注册人脸"""
        self.embeddings_db[name] = np.array(embedding)
        return True

    def recognize(self, embedding):
        """识别人脸（1:N比对）"""
        if not self.embeddings_db:
            return None, 0

        query = np.array(embedding)
        best_name = None
        best_similarity = 0

        for name, stored_emb in self.embeddings_db.items():
            similarity = 1 - cosine(query, stored_emb)
            if similarity > best_similarity:
                best_similarity = similarity
                best_name = name

        if best_similarity >= self.threshold:
            return best_name, best_similarity
        return None, best_similarity

    def verify(self, embedding1, embedding2):
        """验证人脸（1:1比对）"""
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)
        similarity = 1 - cosine(emb1, emb2)
        return similarity >= self.threshold, similarity
```

---

## 七、与现有系统集成

### 7.1 数据复用

**复用现有数据库**：
- 路径: `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\face_checkin.db`
- 表: `enrollments`, `checkins`

**复用现有操作员数据**：
- 从调度中心（5003）同步操作员列表
- 通过姓名自动匹配 operator_id

### 7.2 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 现有人脸考勤 | 5009 | TensorFlow.js方案 |
| **INSIGHTFACE服务** | **5010** | 新增（可复用5009） |
| 调度中心 | 5003 | 操作员数据源 |
| 容器中心 | 5002 | 考勤记录存储 |

### 7.3 通知集成

复用现有通知逻辑：
1. 识别成功后 → 查询调度中心操作员
2. 推送消息到企业微信
3. 创建容器中心工单记录

---

## 八、部署步骤

### 8.1 环境准备
1. 安装Anaconda
2. 创建Python 3.9环境
3. 安装依赖包

### 8.2 模型下载
```bash
# 方式1：自动下载（首次运行）
python -c "from insightface.app import FaceAnalysis; app = FaceAnalysis(name='buffalo_l'); app.prepare(ctx_id=0)"

# 方式2：手动下载
wget https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
unzip buffalo_l.zip -d ~/.insightface/models/
```

### 8.3 代码部署
1. 创建 `face_insight_service.py`
2. 集成到 `face_server.py`
3. 配置端口5010
4. 更新 `server_launcher.py`

### 8.4 测试验证
```bash
# 启动服务
python face_server.py --port 5009 --engine insightface

# 访问测试页面
http://localhost:5009/face/app/
```

---

## 九、性能优化

### 9.1 GPU加速
```python
# ctx_id=0 使用GPU，ctx_id=-1 使用CPU
app.prepare(ctx_id=0, det_size=(640, 640))
```

### 9.2 批量处理
```python
# 支持批量识别
def recognize_batch(self, img_list):
    results = []
    for img in img_list:
        faces = self.engine.detect_faces(img)
        # ... 处理
    return results
```

### 9.3 缓存优化
- 特征向量数据库常驻内存
- SQLite索引优化
- 连接池复用

---

## 十、常见问题处理

### 10.1 模型下载失败
**问题**：SSL证书错误
**解决**：
```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### 10.2 CUDA版本不匹配
**问题**：onnxruntime-gpu报错
**解决**：
```bash
# 确认CUDA版本
nvcc --version

# 安装对应版本
pip install onnxruntime-gpu==1.16.0 --extra-index-url https://pypi.ngc.nvidia.com
```

### 10.3 np.int弃用错误
**问题**：AttributeError: module 'numpy' has no attribute 'int'
**解决**：
```bash
# 降级numpy
pip install numpy==1.22.3
```

---

## 十一、验收标准

- [ ] INSIGHTFACE模型下载成功
- [ ] 人脸注册功能正常
- [ ] 人脸识别准确率 > 99%
- [ ] 与调度中心数据同步正常
- [ ] 考勤通知推送到企业微信
- [ ] 支持100+人员注册
- [ ] 单次识别延迟 < 500ms（CPU）

---

## 十二、后续扩展

### 12.1 活体检测
- 集成眨眼、点头等动作检测
- 防止照片/视频欺骗

### 12.2 考勤规则
- 排班管理
- 迟到早退判定
- 请假集成

### 12.3 数据分析
- 考勤统计报表
- 异常考勤预警
- 人员考勤趋势

---

## 附录：模型文件清单

```
d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\models\buffalo_l\
├── buffalo_l.zip                    # 压缩包（160MB）
├── 2d106det/
│   └── 2d106det.onnx              # 106点关键点检测（~10MB）
├── det_10g.onnx                    # 人脸检测模型（~10MB）
├── w600k_r50.onnx                  # 人脸识别模型（~130MB）
├── genderage.onnx                  # 性别年龄预测（~5MB）
└── buffalo_l.json                   # 模型配置
```

**总计约：160MB**
