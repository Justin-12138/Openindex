"""
项目常量定义

集中管理所有硬编码的常量值，便于维护和配置。
"""

# =============================================================================
# PDF 相关常量
# =============================================================================

# PDF 默认尺寸 (Letter 纸张, 单位: 点)
PDF_DEFAULT_WIDTH = 612
PDF_DEFAULT_HEIGHT = 792

# A4 纸张尺寸 (单位: 点)
PDF_A4_WIDTH = 595
PDF_A4_HEIGHT = 842

# MinerU 内部坐标系尺寸
MINERU_INTERNAL_WIDTH = 1000
MINERU_INTERNAL_HEIGHT = 1000

# =============================================================================
# 树处理默认值
# =============================================================================

# 树剪枝 token 阈值（低于此值的节点可能被合并）
DEFAULT_TOKEN_THRESHOLD = 5000

# 摘要生成 token 阈值（超过此值的节点生成摘要）
DEFAULT_SUMMARY_THRESHOLD = 200

# 默认树节点层级深度限制
DEFAULT_MAX_DEPTH = 10

# =============================================================================
# API 默认值
# =============================================================================

# 查询返回的默认节点数量
DEFAULT_TOP_K = 5

# 对话历史最大保留条数
DEFAULT_MAX_HISTORY = 10

# 默认 API 端口
DEFAULT_API_PORT = 8090

# 默认 API 主机
DEFAULT_API_HOST = "0.0.0.0"

# =============================================================================
# 文件处理常量
# =============================================================================

# 默认最大文件大小 (100MB)
DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024

# 允许的文件扩展名
ALLOWED_EXTENSIONS = [".pdf"]

# 默认消息最大长度
DEFAULT_MAX_MESSAGE_LENGTH = 10000

# 文件名最大长度
MAX_FILENAME_LENGTH = 100

# =============================================================================
# LLM 相关常量
# =============================================================================

# 默认最大并发请求数
DEFAULT_MAX_CONCURRENT_REQUESTS = 5

# 默认请求超时时间（秒）
DEFAULT_REQUEST_TIMEOUT = 120

# 默认最大重试次数
DEFAULT_MAX_RETRIES = 3

# 默认重试延迟（秒）
DEFAULT_RETRY_DELAY = 1.0

# 默认温度参数
DEFAULT_TEMPERATURE = 0.7

# 默认 LLM 模型
DEFAULT_LLM_MODEL = "glm-4.7"

# =============================================================================
# 数据库相关常量
# =============================================================================

# 默认数据库文件名
DEFAULT_DB_FILENAME = "openindex.db"

# 文档状态
class DocumentStatus:
    PENDING = "pending"
    PARSING = "parsing"
    READY = "ready"
    ERROR = "error"

# 解析任务状态
class ParseJobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# 消息角色
class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

# =============================================================================
# 解析器相关常量
# =============================================================================

# MinerU 默认后端
DEFAULT_MINERU_BACKEND = "vlm-http-client"

# MinerU 输出目录名
MINERU_OUTPUT_DIR = "mineru"

# VLM 子目录名
VLM_SUBDIR = "vlm"

# 内容列表文件名后缀
CONTENT_LIST_SUFFIX = "_content_list.json"
CONTENT_LIST_V2_SUFFIX = "_content_list_v2.json"
MIDDLE_JSON_SUFFIX = "_middle.json"
