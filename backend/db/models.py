from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, SmallInteger
from datetime import datetime
from db.session import Base


# 软删除标记 + 操作：is_deleted/deleted_at，配合 CRUD 软删/恢复/purge 语义
class SoftDeleteMixin:
    is_deleted = Column(SmallInteger, nullable=False, default=0, server_default="0",
                        comment="是否删除: 0正常 1已删除")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    def soft_delete(self):
        self.is_deleted = 1
        self.deleted_at = datetime.now()

    def restore(self):
        self.is_deleted = 0
        self.deleted_at = None


# 患者表
class Patient(SoftDeleteMixin, Base):
    __tablename__ = "patient"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name = Column(String(50), comment="患者姓名")
    age = Column(Integer, comment="年龄")
    gender = Column(String(10), comment="性别")
    phone = Column(String(20), index=True, comment="联系电话")
    # 账号认领关系：删账号解绑（SET NULL），档案与医疗数据归属医院/医生，不被级联销毁
    user_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), default=None,
                     index=True, comment="关联用户ID（患者角色关联）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

# 电子病历表
class MedicalRecord(SoftDeleteMixin, Base):
    __tablename__ = "medical_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 病历依附患者：删患者级联删其整条病历链
    patient_id = Column(Integer, ForeignKey("patient.id", ondelete="CASCADE"),
                        index=True, comment="关联患者ID")
    raw_text = Column(Text, comment="原始自由文本病历")
    structured_data = Column(JSON, comment="AI结构化抽取结果（症状、病史、诊断）")
    dicom_file_path = Column(String(255), comment="DICOM影像存储路径")
    create_time = Column(DateTime, default=datetime.now)

# 医学文献表
class MedicalPaper(Base):
    __tablename__ = "medical_paper"
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_name = Column(String(200), comment="文献标题")
    file_path = Column(String(255), comment="PDF文件路径")
    full_text = Column(Text, comment="PDF提取的全文内容")
    ai_summary = Column(Text, comment="AI生成摘要")
    core_conclusion = Column(Text, comment="核心研究结论")
    create_time = Column(DateTime, default=datetime.now)

# 诊断报告表
class DiagnosisReport(SoftDeleteMixin, Base):
    __tablename__ = "diagnosis_report"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 报告依附病历：删病历级联删其报告
    record_id = Column(Integer, ForeignKey("medical_record.id", ondelete="CASCADE"),
                       index=True, comment="关联病历ID")
    image_analysis = Column(Text, comment="影像分析结果")
    diagnosis_suggest = Column(Text, comment="AI鉴别诊断建议")
    pdf_path = Column(String(255), comment="导出PDF报告路径")
    create_time = Column(DateTime, default=datetime.now)

# 问诊对话会话表
class ConsultSession(Base):
    __tablename__ = "consult_session"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), comment="对话标题（首句摘要）")
    department = Column(String(50), comment="问诊科室")
    # 会话是账号一次性数据：删账号连带清会话，避免永存孤儿
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"),
                     index=True, comment="用户ID")
    message_count = Column(Integer, default=0, comment="消息数")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# 问诊对话消息表
class ConsultMessage(Base):
    __tablename__ = "consult_message"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 消息依附会话：删会话自动清消息
    session_id = Column(Integer, ForeignKey("consult_session.id", ondelete="CASCADE"),
                        index=True, comment="会话ID")
    role = Column(String(20), comment="user/assistant")
    content = Column(Text, comment="消息内容")
    create_time = Column(DateTime, default=datetime.now)

# 医疗知识库（RAG检索用）
class MedicalKnowledge(Base):
    __tablename__ = "medical_knowledge"
    id = Column(Integer, primary_key=True, autoincrement=True)
    disease_name = Column(String(100), comment="疾病名称")
    guide_content = Column(Text, comment="临床指南内容")
    vector_id = Column(String(100), comment="Milvus向量索引ID")

# 系统用户表（JWT认证）
class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="登录名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), comment="真实姓名")
    role = Column(String(20), default="doctor", comment="角色: admin/doctor/patient")
    department = Column(String(100), comment="科室")
    is_active = Column(Integer, default=1, comment="是否启用: 1启用 0禁用")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

# 疾病字典表（用于仪表盘疾病名称映射）
class DiseaseDict(Base):
    __tablename__ = "disease_dict"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), comment="病历中匹配的关键词")
    disease_name = Column(String(100), comment="标准化疾病名称")