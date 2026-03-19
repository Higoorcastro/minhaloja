import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Plano(db.Model):
    __tablename__ = 'planos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    preco_mensal = db.Column(db.Numeric(10, 2), default=0)
    max_usuarios = db.Column(db.Integer, default=5)
    modulos = db.Column(db.Text, default='dashboard,pdv,vendas,produtos,clientes')
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    tenants = db.relationship('Tenant', backref='plano', lazy='dynamic')

class Tenant(db.Model):
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(20))
    email = db.Column(db.String(255))
    telefone = db.Column(db.String(20))
    plano_id = db.Column(db.Integer, db.ForeignKey('planos.id'))
    status = db.Column(db.String(20), default='ATIVO') # ATIVO, SUSPENSO, CANCELADO
    data_vencimento = db.Column(db.Date)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    usuarios = db.relationship('TenantUsuario', backref='tenant', cascade='all, delete-orphan', lazy='dynamic')

class TenantUsuario(db.Model):
    __tablename__ = 'tenant_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    login = db.Column(db.String(100), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    papel = db.Column(db.String(50), default='operador') # admin, operador
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # __table_args__ = (db.UniqueConstraint('tenant_id', 'login', name='_tenant_login_uc'),)

class SuperadminUsuario(db.Model):
    __tablename__ = 'superadmin_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    login = db.Column(db.String(100), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class ContatoLead(db.Model):
    __tablename__ = 'contato_leads'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(30))
    empresa = db.Column(db.String(255))
    plano_interesse = db.Column(db.String(50))
    mensagem = db.Column(db.Text)
    # NOVO, CONTATADO, FECHADO, DESCARTADO
    status = db.Column(db.String(20), default='NOVO')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
