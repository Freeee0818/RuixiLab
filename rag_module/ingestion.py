"""多格式知识文件的解析、增量切块与向量入库流程。

``DataIngestor`` 扫描原始资料目录和实验元数据目录，将 PDF、PPTX、表格、JSON、
纯文本及 DOCX 统一转换成 LlamaIndex ``Document``，再交给 ``StructuredChunker``
生成父子块，最后通过 ``RAGService`` 写入 Qdrant。

模块使用文件 SHA-256 作为内容版本，并在 ``.ingestion_index.json`` 中保存本地入库
状态。未变化的文件会被跳过，修改后的文件采用“先写新版本、再删旧版本”的顺序，
磁盘上已删除的来源也会从向量库同步清除。
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from pptx import Presentation
from llama_index.core import Document
from llama_index.readers.file import PDFReader, UnstructuredReader, DocxReader
from rag_module.service import rag_service
from rag_module.chunking import StructuredChunker, file_fingerprint
from config.settings import settings
from datetime import datetime

# pdfplumber 和 OCR 工具属于可选的 PDF 降级能力。把导入放在 try 中，允许只处理
# 普通文本 PDF/其他格式的部署在未安装这些系统依赖时仍可启动。
try:
  import pdfplumber
  PDFPLUMBER_AVAILABLE = True
except ImportError:
  PDFPLUMBER_AVAILABLE = False

try:
  from pdf2image import convert_from_path
  import pytesseract
  # Windows 安装器的默认位置通常不在 PATH；Linux 则沿用系统 PATH 中的命令。
  import platform
  if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  OCR_AVAILABLE = True
except ImportError:
  OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


class DataIngestor:
  """协调知识库文件发现、格式解析、增量判断和向量库同步。

  一个实例持有一份内存中的入库索引 ``file_index``。模块底部创建了共享
  ``ingestor``，命令行入库脚本直接复用该实例。
  """

  def __init__(self):
    """从全局配置解析知识库目录，并读取已有入库索引。"""
    self.raw_dir = Path(settings.RAG_RAW_DIR)
    # parsed_dir 由知识库目录约定保留；当前解析流程直接生成内存 Document，暂不
    # 在这里落中间文本文件。
    self.parsed_dir = Path(settings.RAG_PARSED_DIR)
    self.meta_dir = Path(settings.RAG_META_DIR)

    # 索引放在 raw_dir 中且以点开头；扫描时会主动跳过隐藏文件，避免把索引本身
    # 当成知识文档再次导入。
    self.index_file = self.raw_dir / ".ingestion_index.json"
    self.file_index = self._load_index()

  def _load_index(self) -> Dict[str, Dict[str, Any]]:
    """加载持久化入库索引；首次运行或索引不存在时返回空字典。"""
    if self.index_file.exists():
      with open(self.index_file, 'r', encoding='utf-8') as f:
        return json.load(f)
    return {}

  def _save_index(self):
    """把当前入库索引以可读的 UTF-8 JSON 写回磁盘。"""
    with open(self.index_file, 'w', encoding='utf-8') as f:
      json.dump(self.file_index, f, indent=2, ensure_ascii=False)

  def _file_key(self, file_path: Path) -> str:
    """生成与部署绝对路径无关的稳定来源键。

    键使用 ``raw/`` 或 ``meta/`` 前缀区分两个根目录，并统一采用 POSIX 分隔符。
    这样知识库整体迁移到另一台机器后，来源标识仍保持一致。

    Raises:
      ValueError: 文件不属于任何允许扫描的知识库根目录。
    """
    for prefix, root in (("raw", self.raw_dir), ("meta", self.meta_dir)):
      try:
        return f"{prefix}/{file_path.relative_to(root).as_posix()}"
      except ValueError:
        continue
    raise ValueError(f"文件不在知识库目录中: {file_path}")

  def _get_file_hash(self, file_path: Path) -> str:
    """返回文件内容 SHA-256；该值同时作为入库版本号。"""
    return file_fingerprint(file_path)

  def _is_file_changed(self, file_path: Path) -> bool:
    """判断文件是新增内容，或内容哈希与上次成功入库时不同。"""
    file_key = self._file_key(file_path)

    if file_key not in self.file_index:
      return True  # 新文件

    # 不依赖 mtime：复制、解压或时钟变化不会引发无意义重建，真正的内容修改也
    # 不会因时间戳恰好相同而漏掉。
    current_hash = self._get_file_hash(file_path)
    return current_hash != self.file_index[file_key].get('hash')

  def _record_file(self, file_path: Path, doc_count: int, chunk_count: int, version: str):
    """记录一次成功入库的版本及统计信息，并立即持久化索引。"""
    file_key = self._file_key(file_path)
    self.file_index[file_key] = {
      'hash': version,
      'imported_at': datetime.now().isoformat(),
      'doc_count': doc_count,
      'chunk_count': chunk_count,
      'file_name': file_path.name
    }
    self._save_index()

  def _parse_file(self, file_path: Path) -> List[Document]:
    """根据小写扩展名分派到对应格式解析器。

    不支持的格式只记录警告并返回空列表，因此同一批次中的其他文档仍可继续入库。
    """
    suffix = file_path.suffix.lower()
    if suffix == '.pdf':
      return self._parse_pdf(file_path)
    if suffix == '.pptx':
      return self._parse_pptx(file_path)
    if suffix in ['.xlsx', '.xls']:
      return self._parse_excel(file_path)
    if suffix == '.csv':
      return self._parse_csv(file_path)
    if suffix == '.json':
      return self._parse_json(file_path)
    if suffix in ['.txt', '.md']:
      return self._parse_txt(file_path)
    if suffix in ['.doc', '.docx']:
      return self._parse_docx(file_path)
    logger.warning(f"❓ 不支持的文件格式: {file_path.name}")
    return []

#文档入库
  def ingest_all_formats(self, force_reimport: bool = False):
    """扫描所有知识文件，并把本地目录与 Qdrant 增量同步。

    Args:
      force_reimport: 是否忽略已有哈希记录，强制重新解析并写入所有文件。稳定点 ID
        仍会保证相同文件版本的写入是幂等的。

    Notes:
      单个文件解析失败会被记录并跳过，不会中止整批任务。更新文件时，只有新版本
      完成 upsert 后才删除旧版本；只有成功写入的文件才更新本地索引。
    """
    logger.info(f"开始扫描并导入 {self.raw_dir} 与 {self.meta_dir} 下的文档...")

    if force_reimport:
      logger.warning("⚠️  强制重新导入模式：将重新导入所有文件")

    if not self.raw_dir.exists() and not self.meta_dir.exists():
      logger.error("原始文档目录和实验元数据目录都不存在")
      return

    # 先确认向量库真实状态。如果集合为空但磁盘索引声称文件已导入，说明向量目录
    # 可能被清空/迁移，必须丢弃旧状态并全量恢复，不能错误地跳过所有文件。
    rag_service.initialize()
    if rag_service.collection_count() == 0 and self.file_index:
      logger.warning("向量集合为空，忽略旧的入库状态并重新扫描全部文档")
      self.file_index = {}
    # 每轮入库统一复用一组切块器，确保所有格式使用相同的父子块尺度。
    chunker = StructuredChunker(
      parent_chunk_size=settings.RAG_PARENT_CHUNK_SIZE,
      child_chunk_size=settings.RAG_CHILD_CHUNK_SIZE,
      child_chunk_overlap=settings.RAG_CHILD_CHUNK_OVERLAP,
    )

    total_docs = 0
    total_chunks = 0
    skipped_files = 0
    new_files = 0
    updated_files = 0

    # seen_file_keys 不只包含成功解析的文件，也包含扫描到但暂不支持/解析失败的文件；
    # 这样一次临时解析故障不会误删其上次已成功入库的旧数据。
    seen_file_keys = set()
    roots = [root for root in (self.raw_dir, self.meta_dir) if root.exists()]
    for file_path in (path for root in roots for path in root.rglob('*')):
      if file_path.is_file() and not file_path.name.startswith('.'):
        file_key = self._file_key(file_path)
        seen_file_keys.add(file_key)
        # 增量模式只处理新增或哈希变化的文件。
        if not force_reimport and not self._is_file_changed(file_path):
          skipped_files += 1
          logger.debug(f"⏭️  跳过未修改文件: {file_path.name}")
          continue

        # 在成功写入前判断是新增还是更新，仅用于统计和日志。
        is_new = file_key not in self.file_index

        try:
          docs = self._parse_file(file_path)
          if docs:
            version = self._get_file_hash(file_path)
            chunks = chunker.chunk_documents(
              docs,
              file_key=file_key,
              ingestion_version=version,
            )
            if not chunks:
              logger.warning(f"未生成有效文本块: {file_path.name}")
              continue
            # 更新顺序非常关键：先写入带新版本 ID 的点，确认完成后才清理旧版本。
            chunk_count = rag_service.upsert_chunks(chunks)
            rag_service.prune_source_versions(file_key, version)
            total_docs += len(docs)
            total_chunks += chunk_count

            # 向量写入和旧版本清理都成功后，才把新哈希记入本地索引。
            self._record_file(file_path, len(docs), chunk_count, version)

            if is_new:
              new_files += 1
              logger.info(f"✅ 新增 {file_path.name}: {len(docs)} 个文档 / {chunk_count} 个子块")
            else:
              updated_files += 1
              logger.info(f"🔄 更新 {file_path.name}: {len(docs)} 个文档 / {chunk_count} 个子块")

        except Exception as e:
          logger.error(f"❌ 解析失败 {file_path.name}: {str(e)}")

    # 索引有记录但本次两个根目录都未扫描到的来源，视为用户已从知识库删除。
    removed_keys = set(self.file_index) - seen_file_keys
    for file_key in removed_keys:
      rag_service.delete_source(file_key)
      self.file_index.pop(file_key, None)
      logger.info(f"🗑️ 已删除知识库中不存在的来源: {file_key}")

    self._save_index()

    logger.info("\n========== 导入完成 ==========")
    logger.info(f"✅ 新增文件: {new_files} 个")
    logger.info(f"🔄 更新文件: {updated_files} 个")
    logger.info(f"⏭️  跳过文件: {skipped_files} 个")
    logger.info(f"📦 共导入文档: {total_docs} 个，子块: {total_chunks} 个")
    logger.info(f"🔎 当前向量点数: {rag_service.collection_count()}")
    logger.info(f"💾 索引已保存至: {self.index_file}")

  def _parse_pdf(self, file_path: Path) -> List[Document]:
    """按成本从低到高解析 PDF，并在必要时使用 OCR。

    降级顺序为 LlamaIndex ``PDFReader`` -> pdfplumber -> Tesseract OCR ->
    ``UnstructuredReader``。任一步得到足量文本就立即返回；每页/每份文档都附加
    来源与提取方式元数据，方便检索结果回溯和排错。
    """
    documents = []

    # 方法 1：使用 PDFReader 直接读取 PDF 内嵌文本，速度最快且通常最准确。
    try:
      reader = PDFReader()
      documents = reader.load_data(file=str(file_path))

      # 解析器即使没有读到正文也可能返回 Document，因此用 50 字符作为“确有文本”
      # 的宽松判据，而不是只判断列表非空。
      has_text = any(doc.text and len(doc.text.strip()) > 50 for doc in documents)

      if has_text:
        # 保留 PDFReader 自带元数据（例如页码），这里只补充统一来源字段。
        for doc in documents:
          doc.metadata.update({
            "source_type": "pdf",
            "file_name": file_path.name,
            "file_path": str(file_path),
            "extraction_method": "text"
          })
        logger.info(f"📄 {file_path.name}: 文本提取成功")
        return documents
      else:
        logger.warning(f"⚠️  {file_path.name}: 文本提取为空，尝试 OCR...")
    except Exception as e:
      logger.warning(f"⚠️  {file_path.name}: 文本提取失败 ({e})，尝试 OCR...")

    # 方法 2：pdfplumber 对部分排版复杂或 PDFReader 兼容性较差的文件效果更好。
    if PDFPLUMBER_AVAILABLE:
      try:
        documents = []
        with pdfplumber.open(str(file_path)) as pdf:
          for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()

            if text and len(text.strip()) > 50:
              doc = Document(
                text=text,
                metadata={
                  "source_type": "pdf",
                  "file_name": file_path.name,
                  "file_path": str(file_path),
                  "page_label": str(page_num),
                  "extraction_method": "pdfplumber"
                }
              )
              documents.append(doc)

        if documents:
          logger.info(f"📄 {file_path.name}: pdfplumber 提取成功 ({len(documents)} 页)")
          return documents
        else:
          logger.warning(f"⚠️  {file_path.name}: pdfplumber 提取为空，尝试 OCR...")
      except Exception as e:
        logger.warning(f"⚠️  {file_path.name}: pdfplumber 失败 ({e})，尝试 OCR...")

    # 方法 3：扫描版 PDF 没有文本层，需要先以 200 DPI 渲染每页再做中英 OCR。
    if OCR_AVAILABLE:
      try:
        logger.info(f"🔍 {file_path.name}: 开始 OCR 识别（可能需要几分钟）...")

        # DPI 越高识别可能越准但内存、时间成本越大；200 是常用折中值。
        images = convert_from_path(str(file_path), dpi=200)

        documents = []
        for page_num, image in enumerate(images, 1):
          # 同时启用简体中文与英文语言包，适合物理讲义中的中英文和变量说明。
          text = pytesseract.image_to_string(image, lang='chi_sim+eng')

          if text and len(text.strip()) > 20:
            doc = Document(
              text=text,
              metadata={
                "source_type": "pdf",
                "file_name": file_path.name,
                "file_path": str(file_path),
                "page_label": str(page_num),
                "extraction_method": "ocr"
              }
            )
            documents.append(doc)

          if page_num % 10 == 0:
            logger.info(f"  OCR 进度: {page_num}/{len(images)} 页")

        if documents:
          logger.info(f"✅ {file_path.name}: OCR 识别成功 ({len(documents)} 页)")
          return documents
        else:
          logger.error(f"❌ {file_path.name}: OCR 识别失败，未提取到文本")
      except Exception as e:
        logger.error(f"❌ {file_path.name}: OCR 识别出错: {e}")
    else:
      logger.error(f"❌ {file_path.name}: OCR 库未安装，无法识别扫描版 PDF")
      logger.error("   请安装: pip install pdf2image pytesseract pillow")
      logger.error("   并安装 Tesseract-OCR: https://github.com/tesseract-ocr/tesseract")

    # 最后尝试通用解析器；它可能依赖额外系统组件，因此放在明确的降级末尾。
    try:
      reader = UnstructuredReader()
      documents = reader.load_data(file=str(file_path))
      for doc in documents:
        doc.metadata.update({
          "source_type": "pdf",
          "file_name": file_path.name,
          "extraction_method": "unstructured"
        })
      if documents:
        logger.info(f"📄 {file_path.name}: UnstructuredReader 成功")
        return documents
    except Exception:
      logger.error(f"❌ {file_path.name}: 所有方法均失败")

    return []

  def _parse_pptx(self, file_path: Path) -> List[Document]:
    """按幻灯片提取 PPTX 文本，每张非空幻灯片生成一个 Document。"""
    prs = Presentation(str(file_path))
    documents = []

    for slide_idx, slide in enumerate(prs.slides, 1):
      text_content = []

      # shape 类型很多，只收集暴露 text 且内容非空的元素；图片中的文字不做 OCR。
      for shape in slide.shapes:
        if hasattr(shape, "text") and shape.text.strip():
          text_content.append(shape.text.strip())

      if text_content:
        content = "\n".join(text_content)
        doc = Document(
          text=content,
          metadata={
            "source_type": "pptx",
            "file_name": file_path.name,
            "slide_number": slide_idx,
            "file_path": str(file_path)
          }
        )
        documents.append(doc)

    return documents

  def _parse_excel(self, file_path: Path) -> List[Document]:
    """按工作表生成 Excel 的结构与前 10 行文本摘要。

    不把整个大表写入向量库，以控制 embedding 长度；完整数据分析属于计算模块的
    职责，这里的目标是让 Agent 能检索表名、列名和代表性内容。
    """
    documents = []

    # 一个 sheet 对应一个 Document，sheet_name 会被切块器归一为来源位置。
    excel_file = pd.ExcelFile(str(file_path))
    for sheet_name in excel_file.sheet_names:
      df = pd.read_excel(excel_file, sheet_name=sheet_name)

      # 将二维表转成带字段标签的自然语言文本，帮助 embedding 理解表格语义。
      content = f"表格名称: {sheet_name}\n"
      content += f"列名: {', '.join(df.columns.tolist())}\n"
      content += f"行数: {len(df)}\n\n"
      content += f"表格内容摘要:\n{df.head(10).to_string()}\n"

      doc = Document(
        text=content,
        metadata={
          "source_type": "excel",
          "file_name": file_path.name,
          "sheet_name": sheet_name,
          "file_path": str(file_path),
          "columns": df.columns.tolist()
        }
      )
      documents.append(doc)

    return documents

  def _parse_csv(self, file_path: Path) -> List[Document]:
    """把 CSV 的列、统计摘要和前 10 行转换为一个可检索 Document。"""
    df = pd.read_csv(str(file_path))

    content = f"CSV 文件: {file_path.name}\n"
    content += f"列名: {', '.join(df.columns.tolist())}\n"
    content += f"行数: {len(df)}\n\n"
    content += f"数据摘要:\n{df.describe().to_string()}\n\n"
    content += f"前10行数据:\n{df.head(10).to_string()}\n"

    doc = Document(
      text=content,
      metadata={
        "source_type": "csv",
        "file_name": file_path.name,
        "file_path": str(file_path),
        "columns": df.columns.tolist()
      }
    )

    return [doc]

  def _parse_json(self, file_path: Path) -> List[Document]:
    """读取 UTF-8 JSON，并用保留层级缩进的文本形式建立索引。"""
    with open(file_path, 'r', encoding='utf-8') as f:
      data = json.load(f)

    # ensure_ascii=False 保留中文字符，缩进有助于让嵌套层级在切块后仍可读。
    content = f"JSON 文件: {file_path.name}\n\n"
    content += json.dumps(data, indent=2, ensure_ascii=False)

    doc = Document(
      text=content,
      metadata={
        "source_type": "json",
        "file_name": file_path.name,
        "file_path": str(file_path)
      }
    )

    return [doc]

  def _parse_txt(self, file_path: Path) -> List[Document]:
    """以常见中英文编码读取 TXT/Markdown 文本。

    依次尝试 UTF-8、GBK、GB2312 和 UTF-16；只有解码错误才切换编码，其他 I/O
    异常由外层捕获并记录。少于 10 个非空字符的内容被视为无有效知识。
    """
    try:
      # 按现代通用编码到中文旧编码的顺序尝试，减少误解码概率。
      encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
      content = None

      for encoding in encodings:
        try:
          with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
          break
        except UnicodeDecodeError:
          continue

      if not content:
        logger.error(f"无法读取 TXT 文件（编码问题）: {file_path.name}")
        return []

      # 过滤占位文件和近似空文件，避免生成没有检索价值的向量点。
      if len(content.strip()) < 10:
        logger.warning(f"TXT 文件内容过短，跳过: {file_path.name}")
        return []

      doc = Document(
        text=content,
        metadata={
          "source_type": "txt",
          "file_name": file_path.name,
          "file_path": str(file_path)
        }
      )

      return [doc]

    except Exception as e:
      logger.error(f"解析 TXT 文件失败: {file_path.name}, 错误: {e}")
      return []

  def _parse_docx(self, file_path: Path) -> List[Document]:
    """解析 DOCX；旧版二进制 DOC 仅给出转换提示。

    LlamaIndex ``DocxReader`` 支持 OOXML 的 .docx，但不支持传统复合二进制 .doc，
    后者需先由 Word/LibreOffice 转换，避免在服务端隐式依赖办公软件。
    """
    try:
      # 扩展名路由允许 .doc 进入此方法，但这里明确拒绝不兼容格式。
      if file_path.suffix.lower() == '.doc':
        logger.warning(f"⚠️  .doc 格式需要手动转换为 .docx: {file_path.name}")
        logger.warning("   建议: 用 Word 打开后另存为 .docx 格式")
        return []

      # DocxReader 可能按内部结构返回一个或多个 Document。
      reader = DocxReader()
      documents = reader.load_data(file=str(file_path))

      # 在保留解析器原元数据的基础上补充统一来源字段。
      for doc in documents:
        doc.metadata.update({
          "source_type": "docx",
          "file_name": file_path.name,
          "file_path": str(file_path)
        })

      logger.info(f"📄 {file_path.name}: DOCX 提取成功")
      return documents

    except Exception as e:
      logger.error(f"解析 DOCX 文件失败: {file_path.name}, 错误: {e}")
      return []

# 命令行入库脚本使用的共享实例；构造时只读取小型 JSON 索引，不会加载模型。
ingestor = DataIngestor()
