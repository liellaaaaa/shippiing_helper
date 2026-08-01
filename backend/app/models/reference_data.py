from sqlalchemy import Column, Integer, String, Float, Text, UniqueConstraint
from app.database import Base


class Pallet(Base):
    __tablename__ = "pallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    dims = Column(String(100))
    weight_kg = Column(Float)
    cbm = Column(Float)


class ContainerSpec(Base):
    __tablename__ = "container_specs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), unique=True, nullable=False)
    max_cbm = Column(Float)
    max_weight_kg = Column(Float)


class DeclarationElement(Base):
    __tablename__ = "declaration_elements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hs_code = Column(String(20), nullable=False, index=True)
    declaration_name = Column(String(200), nullable=False)
    elements_text = Column(Text)

    __table_args__ = (
        UniqueConstraint("hs_code", "declaration_name", name="uq_declaration_elements"),
    )


class IngredientMapping(Base):
    __tablename__ = "ingredient_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cn_names = Column(Text)      # JSON 数组
    en_names = Column(Text)      # JSON 数组
    cas_numbers = Column(Text)   # JSON 数组
    raw = Column(Text)


class TranslationMapping(Base):
    __tablename__ = "translation_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mapping_type = Column(String(50), nullable=False, index=True)
    cn = Column(String(200), nullable=False)
    en = Column(String(200), nullable=False)

    __table_args__ = (
        UniqueConstraint("mapping_type", "cn", name="uq_translation_mappings"),
    )


class MsdsTemplate(Base):
    __tablename__ = "msds_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    template_json = Column(Text)
