// ══════════════════════════════════════════════════════════════
// STATE
// ══════════════════════════════════════════════════════════════
let cart = [];
let allProdutos = [];
let allClientes = [];
let allCategorias = [];
let allVendedores = [];
let currentPage = 'dashboard';
let currentUser = null;  // { id, nome, papel, permissions }
let shopConfig = {};

const ALL_MODULE_LABELS = {
  dashboard: 'Dashboard', pdv: 'Ponto de Venda', vendas: 'Vendas',
  os: 'Ordem de Serviço', produtos: 'Produtos', clientes: 'Clientes',
  financeiro: 'Financeiro', relatorios: 'Relatórios',
  settings: 'Configurações'
};
const ALL_MODULE_ICONS = {
  dashboard: '🏠', pdv: '🛒', vendas: '📋', os: '🔧', produtos: '📦',
  clientes: '👥', financeiro: '💰', relatorios: '📊',
  settings: '⚙️'
};

const MODULE_SUBS = {
  financeiro: { 'financeiro:fluxo': 'Fluxo de Caixa', 'financeiro:receber': 'Contas a Receber' },
  relatorios: { 'relatorios:vendas': 'Relat. Vendas', 'relatorios:financeiro': 'Relat. Financeiro', 'relatorios:estoque': 'Relat. Estoque' },
  settings: {
    'settings:geral': 'Loja/Dados', 'settings:vendedores': 'Vendedores',
    'settings:maquininhas': 'Maquininhas', 'settings:usuarios': 'Usuários', 'settings:contas': 'Contas'
  }
};

const fmt = n => 'R$ ' + parseFloat(n || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtN = n => parseFloat(n || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const parseMoney = s => {
  if (typeof s !== 'string') return parseFloat(s || 0);
  let v = s.replace(/\D/g, '');
  return v ? parseFloat(v) / 100 : 0;
};
const maskMoney = v => {
  let n = parseMoney(v);
  return n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const today = () => new Date().toISOString().split('T')[0];
const firstDay = () => { const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0]; };
// ── Mobile Menu Toggle ─────────────────────────────────────────
function toggleMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  if (sidebar.classList.contains('mobile-open')) closeMobileMenu();
  else openMobileMenu();
}

function openMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('mobile-backdrop');
  if (!sidebar || !backdrop) return;
  sidebar.classList.add('mobile-open');
  backdrop.style.display = 'block';
  setTimeout(() => backdrop.style.opacity = '1', 10);
}

function closeMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('mobile-backdrop');
  if (!sidebar || !backdrop) return;
  sidebar.classList.remove('mobile-open');
  backdrop.style.opacity = '0';
  setTimeout(() => backdrop.style.display = 'none', 300);
}

// ── Clock ──────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' }) +
    '  ' + now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
setInterval(updateClock, 1000); updateClock();

// ── Sidebar ────────────────────────────────────────────────────
let sidebarCollapsed = false;
function toggleSidebar() {
  sidebarCollapsed = !sidebarCollapsed;
  document.getElementById('sidebar').classList.toggle('collapsed', sidebarCollapsed);
}

// ── Notification ───────────────────────────────────────────────
function notify(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `notif-item ${type}`;
  el.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span><span>${msg}</span>`;
  document.getElementById('notif').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Modal ──────────────────────────────────────────────────────
function openModal(title, html, footer = '', size = 'modal-md') {
  const box = document.getElementById('modal-box');
  box.className = `modal ${size}`;
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-footer').innerHTML = footer;
  document.getElementById('modal-overlay').classList.add('open');
}
function closeModal() { document.getElementById('modal-overlay').classList.remove('open'); }
function modalClickOutside(e) { if (e.target === document.getElementById('modal-overlay')) closeModal(); }

// ── API ─────────────────────────────────────────────────────────
async function api(url, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  if (r.status === 401) { window.location.href = '/login'; return null; }
  if (r.status === 403) { notify('Sem permissão para esta ação', 'error'); return null; }
  const data = await r.json();
  if (!r.ok) {
    const msg = data.error || 'Erro desconhecido no servidor';
    notify(msg, 'error');
    if (data.traceback) {
      console.error('Server Traceback:', data.traceback);
    }
    return data; // Return full object so pages can handle errors
  }
  return data;
}

// ── Auth ───────────────────────────────────────────────────────
async function initAuth() {
  const me = await fetch('/api/auth/me').then(r => r.ok ? r.json() : null);
  if (!me || !me.logged_in) { window.location.href = '/login'; return; }
  currentUser = me;
  document.getElementById('user-display-name').textContent = me.nome;
  document.getElementById('user-display-role').textContent = me.papel === 'admin' ? '👑 Administrador' : '👤 Operador';
  document.getElementById('user-avatar-init').textContent = me.nome.charAt(0).toUpperCase();

  // Gestão section
  if (me.papel === 'admin' || me.permissions.includes('settings')) {
    document.getElementById('nav-section-gestao').style.display = '';
    document.getElementById('nav-settings').style.display = '';
  }

  // Financeiro section
  if (me.papel === 'admin' || me.permissions.includes('financeiro') || me.permissions.includes('receber')) {
    // Financeiro view handles all sub-tabs now
  }

  // Hide unauthorized nav items
  document.querySelectorAll('.nav-item[data-page]').forEach(el => {
    const page = el.dataset.page;
    if (!me.permissions.includes(page)) {
      // Financeiro hub também acessível via permissão 'receber'
      if (page === 'financeiro' && me.permissions.includes('receber')) {
        el.style.display = '';
      } else {
        el.style.display = 'none';
      }
    } else {
      el.style.display = '';
    }
  });

  await initShopConfig();
  if (me.papel !== 'admin' && !me.permissions.includes('dashboard') && me.permissions.length > 0) {
    navigate(me.permissions[0]);
  } else {
    navigate('dashboard');
  }
}

async function initShopConfig() {
  const config = await api('/api/config');
  if (config) {
    shopConfig = config;
    document.getElementById('sidebar-shop-name').textContent = config.shop_name || 'LojaUp';
    if (config.shop_logo) {
      const sidebarLogo = document.getElementById('sidebar-logo');
      if (sidebarLogo) sidebarLogo.src = config.shop_logo;
    }
  }
}

async function doLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
}

function showChangePassword() {
  openModal('Alterar Senha', `
    <div class="form-grid" style="grid-template-columns:1fr">
      <div class="form-group"><label>Senha Atual</label><input type="password" id="cp-atual" placeholder="••••••••"></div>
      <div class="form-group"><label>Nova Senha</label><input type="password" id="cp-nova" placeholder="••••••••"></div>
      <div class="form-group"><label>Confirmar Nova Senha</label><input type="password" id="cp-conf" placeholder="••••••••"></div>
    </div>
  `, `<button class="btn" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-primary" onclick="doChangePassword()">Salvar</button>`, 'modal-sm');
}

async function doChangePassword() {
  const atual = document.getElementById('cp-atual')?.value || '';
  const nova = document.getElementById('cp-nova')?.value || '';
  const conf = document.getElementById('cp-conf')?.value || '';
  if (!atual || !nova) { notify('Preencha todos os campos', 'error'); return; }
  if (nova !== conf) { notify('As senhas não conferem', 'error'); return; }
  if (nova.length < 8) { notify('Nova senha deve ter ao menos 8 caracteres', 'error'); return; }
  const r = await api('/api/auth/change_password', 'POST', { senha_atual: atual, nova_senha: nova });
  if (r?.ok) { notify('Senha alterada com sucesso!', 'success'); closeModal(); }
  else notify(r?.message || 'Erro ao alterar senha', 'error');
}

// ── Navigate ───────────────────────────────────────────────────
let _navigating = false;
const _renderMap = {}; // filled after render functions are defined

function _showProgress(pct) {
  const bar = document.getElementById('nav-progress');
  if (!bar) return;
  bar.classList.add('active');
  bar.style.width = pct + '%';
}
function _hideProgress() {
  const bar = document.getElementById('nav-progress');
  if (!bar) return;
  bar.style.width = '100%';
  setTimeout(() => { bar.style.opacity = '0'; setTimeout(() => { bar.style.width = '0'; bar.classList.remove('active'); }, 300); }, 150);
}

async function navigate(page) {
  try {
    if (currentUser && currentUser.papel !== 'admin' && !currentUser.permissions.includes(page)) {
      notify('Sem permissão para acessar este módulo', 'error'); return;
    }
    if (_navigating) return;
    _navigating = true;

    // 1. Immediate UI Feedback (Sidebar & Title)
    currentPage = page;
    const navItems = document.querySelectorAll('.nav-item');
    let activeEl = null;

    navItems.forEach(el => {
      const isActive = el.dataset.page === page;
      el.classList.toggle('active', isActive);
      if (isActive) activeEl = el;
    });

    const rail = document.getElementById('nav-rail');
    if (rail && activeEl) {
      rail.style.display = 'block';
      rail.style.top = activeEl.offsetTop + 'px';
      rail.style.height = activeEl.offsetHeight + 'px';
    }

    const titles = {
      dashboard: 'Dashboard', pdv: 'Ponto de Venda', vendas: 'Vendas', os: 'Ordens de Serviço',
      produtos: 'Produtos', categorias: 'Categorias', clientes: 'Clientes', financeiro: 'Financeiro', receber: 'A Receber',
      relatorios: 'Relatórios', usuarios: 'Gerenciamento de Usuários', settings: 'Configurações do Sistema'
    };
    document.getElementById('page-title').textContent = titles[page] || page;
    document.getElementById('topbar-actions').innerHTML = '';

    _showProgress(30);

    // 2. Clear content after quick exit animation to avoid "freeze"
    const content = document.getElementById('content');
    content.classList.add('page-exiting');
    await new Promise(r => setTimeout(r, 120)); // Quick fade out
    content.classList.remove('page-exiting');

    // Crucial: Clear content and show loader BEFORE awaiting the renderer
    content.innerHTML = '<div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div>';
    _showProgress(60);

    const renderer = {
      dashboard: () => renderDashboard(), 
      pdv: () => renderPDV(), 
      vendas: () => renderVendas(), 
      os: () => renderOS(),
      produtos: () => renderProdutos(), 
      categorias: () => renderCategorias(), 
      clientes: () => renderClientes(), 
      financeiro: () => renderFinanceiro(), 
      receber: () => renderFinanceiro(),
      relatorios: () => renderRelatorios(),
      usuarios: async () => { await renderSettings(); switchSettingsTab('usuarios'); },
      settings: () => renderSettings()
    }[page];

    if (renderer) {
      await renderer();
    } else {
      console.error(`[NAV] no renderer found for page: ${page}`);
    }
  } catch (err) {
    console.error("Navigation error:", err);
    document.getElementById('content').innerHTML = '<div class="empty"><div class="empty-icon">⚠️</div><p>Erro ao carregar módulo.</p></div>';
  } finally {
    const content = document.getElementById('content');
    if (content) {
      content.classList.add('page-entering');
      content.addEventListener('animationend', () => content.classList.remove('page-entering'), { once: true });
    }

    _showProgress(100);
    setTimeout(_hideProgress, 300);
    _navigating = false;
    if (typeof closeMobileMenu === 'function') closeMobileMenu();
  }
}

// ══════════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════════
async function renderDashboard() {
  document.getElementById('content').innerHTML = '<div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div>';
  const d = await api('/api/dashboard');
  if (!d || d.ok === false) {
    document.getElementById('content').innerHTML = `
          <div class="empty">
            <div class="empty-icon">❌</div>
            <p>Erro ao carregar dashboard</p>
            ${d?.error ? `<div style="font-size:12px; color:var(--red); margin-top:10px; max-width:80%; word-break:break-word;">${d.error}</div>` : ''}
            ${d?.traceback ? `<button class="btn btn-sm" style="margin-top:10px" onclick="this.nextElementSibling.style.display='block';this.style.display='none'">Ver detalhes técnicos</button><pre style="display:none; text-align:left; font-size:10px; background:var(--bg2); padding:10px; margin-top:10px; border-radius:8px; max-height:300px; overflow:auto; width:90%">${d.traceback}</pre>` : ''}
            <button class="btn btn-primary" style="margin-top:20px" onclick="renderDashboard()">Tentar Novamente</button>
          </div>`;
    return;
  }
  const bars = buildBars(d.vendas_7d);
  const topProd = d.top_produtos.map(p => `<tr><td>${p.nome || '-'}</td><td class="mono">${fmtN(p.qtd)}</td><td class="mono text-green">${fmt(p.total)}</td></tr>`).join('')
    || '<tr><td colspan="3" style="text-align:center;color:var(--text3)">Sem dados</td></tr>';
  document.getElementById('content').innerHTML = `
  <div class="stats-grid">
    <div class="stat-card blue"><div class="stat-icon">💰</div><div class="stat-label">Vendas Hoje</div><div class="stat-value">${fmt(d.vendas_hoje)}</div></div>
    <div class="stat-card green"><div class="stat-icon">📈</div><div class="stat-label">Vendas no Mês</div><div class="stat-value">${fmt(d.vendas_mes)}</div><div class="stat-sub">${d.vendas_count} vendas</div></div>
    <div class="stat-card purple"><div class="stat-icon">🔧</div><div class="stat-label">OS em Aberto</div><div class="stat-value">${d.os_abertas}</div></div>
    <div class="stat-card orange"><div class="stat-icon">💸</div><div class="stat-label">Despesas no Mês</div><div class="stat-value">${fmt(d.despesas_mes)}</div></div>
    <div class="stat-card ${d.lucro_mes >= 0 ? 'green' : 'red'}"><div class="stat-icon">${d.lucro_mes >= 0 ? '✅' : '⚠️'}</div><div class="stat-label">Lucro Bruto Mês</div><div class="stat-value ${d.lucro_mes >= 0 ? 'text-green' : 'text-red'}">${fmt(d.lucro_mes)}</div></div>
    <div class="stat-card ${d.prod_estoque_baixo > 0 ? 'orange' : 'green'}"><div class="stat-icon">${d.prod_estoque_baixo > 0 ? '⚠️' : '📦'}</div><div class="stat-label">Estoque Baixo</div><div class="stat-value">${d.prod_estoque_baixo}</div><div class="stat-sub">abaixo do mínimo</div></div>
  </div>
  <div class="dash-grid">
    <div class="card"><div class="card-header">📊 Vendas — Últimos 7 Dias</div><div class="card-body"><div class="chart-bars">${bars}</div></div></div>
    <div class="card"><div class="card-header">🏆 Top Produtos</div><div class="tbl-wrap"><table><thead><tr><th>Produto</th><th>Qtd</th><th>Total</th></tr></thead><tbody>${topProd}</tbody></table></div></div>
  </div>`;
}

function buildBars(data) {
  if (!data || !data.length) return '<div class="empty" style="width:100%"><div class="empty-icon">📊</div><p>Sem vendas</p></div>';
  const max = Math.max(...data.map(d => d.total), 1);
  return data.map(d => {
    const pct = Math.max(4, (d.total / max) * 130);
    const lbl = d.dia ? d.dia.split('-').slice(1).join('/') : '';
    return `<div class="bar-col"><div class="bar" style="height:${pct}px" data-val="${fmt(d.total)}"></div><div class="bar-lbl">${lbl}</div></div>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════════
// USUARIOS — GERENCIAMENTO
// ══════════════════════════════════════════════════════════════
async function renderUsuarios() {
  const plano = await api('/api/plano/info') || { max_usuarios: 999, modulos: Object.keys(ALL_MODULE_LABELS), total_usuarios: 0 };
  window._planoInfo = plano;
  const restam = plano.max_usuarios - plano.total_usuarios;
  const limiteBadge = plano.max_usuarios < 999
    ? `<span class="badge ${restam <= 1 ? 'badge-red' : 'badge-blue'}" style="font-size:11px">${plano.total_usuarios}/${plano.max_usuarios} usuários</span>`
    : '';
  document.getElementById('topbar-actions').innerHTML = `
    ${limiteBadge}
    <button class="topbar-btn primary" onclick="novoUsuario()" ${restam <= 0 ? 'disabled title="Limite de usuários atingido"' : ''}>+ Novo Usuário</button>
  `;
  document.getElementById('content').innerHTML = `
    <div id="users-grid" class="users-grid">
      <div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div>
    </div>`;
  loadUsuarios();
}

async function loadUsuarios() {
  const data = await api('/api/usuarios');
  if (!data) return;
  const grid = document.getElementById('users-grid');
  if (!data.length) { grid.innerHTML = '<div class="empty"><div class="empty-icon">👥</div><p>Nenhum usuário</p></div>'; return; }
  grid.innerHTML = data.map(u => {
    const permLabels = u.papel === 'admin'
      ? '<span class="badge badge-green">Acesso total</span>'
      : u.permissoes.map(m => `<span class="badge badge-blue" style="font-size:10px">${ALL_MODULE_LABELS[m] || m}</span>`).join(' ') || '<span style="color:var(--text3);font-size:11px">Sem permissões</span>';
    const roleBadge = u.papel === 'admin'
      ? '<span class="badge badge-purple">👑 Admin</span>'
      : '<span class="badge badge-gray">👤 Operador</span>';
    const statusBadge = u.ativo
      ? '<span class="badge badge-green">Ativo</span>'
      : '<span class="badge badge-red">Inativo</span>';
    const isSelf = currentUser && u.id === currentUser.id;
    return `
      <div class="user-card">
        <div class="user-card-avatar">${u.nome.charAt(0).toUpperCase()}</div>
        <div class="user-card-info">
          <div class="user-card-name">${u.nome} ${isSelf ? '<span style="font-size:10px;color:var(--text3)">(você)</span>' : ''}</div>
          <div class="user-card-meta">
            <span class="mono" style="color:var(--text3)">${u.login}</span>
            ${roleBadge} ${statusBadge}
          </div>
          <div class="user-card-perms" style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">${permLabels}</div>
        </div>
        <div class="user-card-actions">
          <button class="btn btn-sm" onclick="editarUsuario(${u.id})">✏️ Editar</button>
          ${!isSelf ? `<button class="btn btn-sm btn-danger" onclick="deletarUsuario(${u.id},'${u.nome}')" title="Excluir Usuário">🗑️ Excluir</button>` : ''}
        </div>
      </div>`;
  }).join('');
}

function buildPermGrid(papel, permissoesSelecionadas = []) {
  const isAdmin = papel === 'admin';
  const planModules = window._planoInfo?.modulos || [];
  const mainModules = Object.keys(ALL_MODULE_LABELS).filter(m => planModules.includes(m));

  return `
    <div class="section-title" style="margin-top:4px">Permissões de Acesso</div>
    ${isAdmin ? `<div style="font-size:12px;color:var(--green);margin-bottom:8px">✅ Administrador tem acesso total (dentro do plano).</div>` : ''}
    <div class="perm-grid-v2">
      ${mainModules.map(m => {
    const checked = isAdmin || permissoesSelecionadas.includes(m);
    const subs = MODULE_SUBS[m] || {};
    return `
        <div class="perm-group" style="background:var(--bg3); border:1px solid var(--border); border-radius:8px; padding:10px; margin-bottom:8px">
          <div class="perm-item ${checked ? 'checked' : ''} ${isAdmin ? 'admin-locked' : ''}" 
               onclick="${isAdmin ? '' : `togglePerm(this,'${m}')`}" data-module="${m}" style="background:none; border:none; padding:0">
            <div class="perm-check">${checked ? '✓' : ''}</div>
            <span class="perm-label" style="font-weight:700">${ALL_MODULE_ICONS[m]} ${ALL_MODULE_LABELS[m]}</span>
          </div>
          
          ${Object.keys(subs).length ? `
          <div class="perm-subs" style="margin-left:26px; margin-top:8px; display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:6px">
            ${Object.entries(subs).filter(([subId]) => planModules.includes(subId)).map(([subId, subLabel]) => {
      const subChecked = isAdmin || permissoesSelecionadas.includes(subId);
      return `
              <div class="perm-item sub-perm ${subChecked ? 'checked' : ''} ${isAdmin ? 'admin-locked' : ''}" 
                   onclick="${isAdmin ? '' : `togglePerm(this,'${subId}')`}" data-module="${subId}" style="padding:4px 8px; font-size:11px">
                <div class="perm-check" style="width:14px; height:14px; font-size:9px">${subChecked ? '✓' : ''}</div>
                <span class="perm-label">${subLabel}</span>
              </div>`;
    }).join('')}
          </div>` : ''}
        </div>`;
  }).join('')}
    </div>`;
}

function toggleSubPerms(parentModule, isChecked) {
  const subs = MODULE_SUBS[parentModule];
  if (!subs) return;
  Object.keys(subs).forEach(subId => {
    const el = document.querySelector(`#modal-body .perm-item[data-module="${subId}"]`);
    if (el) {
      if (isChecked) el.classList.add('checked');
      else el.classList.remove('checked');
      const check = el.querySelector('.perm-check');
      if (check) check.textContent = isChecked ? '✓' : '';
    }
  });
}

function togglePerm(el, module) {
  el.classList.toggle('checked');
  const isChecked = el.classList.contains('checked');
  const check = el.querySelector('.perm-check');
  if (check) check.textContent = isChecked ? '✓' : '';

  // Se for um módulo principal, toggle nos subs
  if (MODULE_SUBS[module]) {
    toggleSubPerms(module, isChecked);
  } else if (module.includes(':')) {
    // Se for um sub, e foi marcado, garante que o pai está marcado
    if (isChecked) {
      const parentId = module.split(':')[0];
      const parentEl = document.querySelector(`#modal-body .perm-item[data-module="${parentId}"]`);
      if (parentEl && !parentEl.classList.contains('checked')) {
        parentEl.classList.add('checked');
        parentEl.querySelector('.perm-check').textContent = '✓';
      }
    }
  }
}

function onPapelChange() {
  const papel = document.getElementById('uf-papel')?.value;
  const permGrid = document.getElementById('perm-grid-wrap');
  if (permGrid) {
    const perms = getSelectedPerms();
    permGrid.innerHTML = buildPermGrid(papel, perms);
  }
}

function getSelectedPerms() {
  // Usa .querySelectorAll no #modal-body para garantir que só pegue as permissões do modal atual
  return Array.from(document.querySelectorAll('#modal-body .perm-item.checked:not(.admin-locked)')).map(el => el.dataset.module);
}

function buildUserForm(u = null) {
  const papel = u?.papel || 'operador';
  return `
    <div class="form-grid">
      <div class="form-group full"><label>Nome Completo *</label><input id="uf-nome" value="${u?.nome || ''}" placeholder="Ex: João Silva"></div>
      <div class="form-group"><label>E-mail *</label><input type="email" id="uf-login" value="${u?.login || ''}" placeholder="joao@exemplo.com" ${u?.id === currentUser?.id ? 'readonly' : ''}></div>
      <div class="form-group"><label>Senha ${u ? '(deixe vazio para manter)' : '*'}</label><input type="password" id="uf-senha" placeholder="${u ? 'Nova senha (opcional)' : 'Mínimo 8 caracteres'}"></div>
      <div class="form-group"><label>Papel</label>
        <select id="uf-papel" onchange="onPapelChange()">
          <option value="operador" ${papel === 'operador' ? 'selected' : ''}>👤 Operador</option>
          <option value="admin" ${papel === 'admin' ? 'selected' : ''}>👑 Administrador</option>
        </select>
      </div>
      <div class="form-group"><label>Status</label>
        <select id="uf-ativo">
          <option value="1" ${(u?.ativo !== 0) ? 'selected' : ''}>✅ Ativo</option>
          <option value="0" ${u?.ativo === 0 ? 'selected' : ''}>❌ Inativo</option>
        </select>
      </div>
    </div>
    <div class="divider"></div>
    <div id="perm-grid-wrap">${buildPermGrid(papel, u?.permissoes || [])}</div>`;
}

async function novoUsuario() {
  openModal('Novo Usuário', buildUserForm(),
    `<button class="btn" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-primary" onclick="salvarUsuario()">Criar Usuário</button>`, 'modal-lg');
}

async function editarUsuario(id) {
  const users = await api('/api/usuarios');
  const u = users?.find(x => x.id === id);
  if (!u) return;
  openModal(`Editar Usuário — ${u.nome}`, buildUserForm(u),
    `<button class="btn" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-primary" onclick="salvarUsuario(${id})">Salvar</button>`, 'modal-lg');
}

async function salvarUsuario(id = null) {
  const nome = document.getElementById('uf-nome')?.value || '';
  const login = document.getElementById('uf-login')?.value || '';
  const senha = document.getElementById('uf-senha')?.value || '';
  const papel = document.getElementById('uf-papel')?.value || 'operador';
  const ativo = parseInt(document.getElementById('uf-ativo')?.value || '1');

  if (!nome || !login) { notify('Nome e login são obrigatórios', 'error'); return; }
  if (!id && !senha) { notify('Senha é obrigatória para novo usuário', 'error'); return; }

  const perms = papel === 'admin' ? [] : getSelectedPerms();
  const payload = { nome, login, papel, ativo, permissoes: perms };
  if (senha) payload.senha = senha;

  const r = id
    ? await api(`/api/usuarios/${id}`, 'PUT', payload)
    : await api('/api/usuarios', 'POST', payload);

  if (r?.ok) {
    notify(id ? 'Usuário atualizado!' : 'Usuário criado!', 'success');
    closeModal();
    loadUsuarios();
  } else {
    notify(r?.message || 'Erro ao salvar', 'error');
  }
}

async function deletarUsuario(id, nome) {
  if (!confirm(`⚠️ ATENÇÃO: Deseja realmente excluir permanentemente o acesso de "${nome}"?`)) return;
  const r = await api(`/api/usuarios/${id}`, 'DELETE');
  if (r?.ok) { notify('Usuário excluído permanentemente', 'warning'); loadUsuarios(); }
  else notify(r?.message || 'Erro ao excluir', 'error');
}

// ══════════════════════════════════════════════════════════════
// PDV
// ══════════════════════════════════════════════════════════════
async function renderPDV() {
  allProdutos = await api('/api/produtos') || [];
  allClientes = await api('/api/clientes') || [];
  allVendedores = await api('/api/vendedores') || [];
  window._allMaquininhas = await api('/api/maquininhas') || [];
  document.getElementById('topbar-actions').innerHTML = `<button class="topbar-btn" onclick="cart=[];renderCart()">🗑 Limpar</button>`;
  document.getElementById('content').innerHTML = `
  <div id="pdv-wrap">
    <div id="pdv-produtos">
      <div id="pdv-search"><input type="text" id="pdv-q" placeholder="🔍 Buscar produto..." oninput="renderProdutosGrid()" style="width:100%"></div>
      <div id="pdv-grid"></div>
    </div>
    <div id="pdv-sidebar">
      <div id="cart-header">🛒 Carrinho<span id="cart-count" class="badge badge-blue">0</span></div>
      <div id="cart"></div>
      <div id="cart-total">
        <div class="total-row"><span>Subtotal</span><span id="sub-val" class="mono">R$ 0,00</span></div>
        <div class="total-row"><span>Desconto (R$)</span><input type="text" id="cart-desconto" value="0,00" oninput="this.value=maskMoney(this.value);updateTotals()" style="width:100px;text-align:right;padding:3px 6px"></div>
        <div class="total-row final"><span>TOTAL</span><span id="total-val">R$ 0,00</span></div>
        <div id="cart-actions"><button class="btn" onclick="showCheckout()">💳 Finalizar</button></div>
      </div>
    </div>
  </div>`;
  renderProdutosGrid(); renderCart();
}

function renderProdutosGrid() {
  const q = (document.getElementById('pdv-q')?.value || '').toLowerCase();
  const prods = allProdutos.filter(p => !q || p.nome.toLowerCase().includes(q) || (p.codigo || '').toLowerCase().includes(q));
  const grid = document.getElementById('pdv-grid');
  if (!grid) return;
  if (!prods.length) { grid.innerHTML = '<div class="empty" style="grid-column:1/-1"><div class="empty-icon">📦</div><p>Nenhum produto encontrado</p></div>'; return; }

  const getIcon = (cat) => {
    const c = (cat || '').toLowerCase();
    if (c.includes('celular') || c.includes('smartphone')) return '📱';
    if (c.includes('info') || c.includes('computador')) return '💻';
    if (c.includes('eletrônico')) return '🔌';
    if (c.includes('acessório')) return '🎧';
    if (c.includes('serviço')) return '🔧';
    if (c.includes('peça')) return '⚙️';
    return '📦';
  };

  grid.innerHTML = prods.map(p => {
    const stockClass = p.estoque <= 0 ? 'stock-none' : (p.estoque <= p.estoque_minimo ? 'stock-low' : 'stock-ok');
    return `
        <div class="produto-card ${p.estoque <= 0 ? 'sem-estoque' : ''}" onclick="addToCart(${p.id})">
          <div class="pc-top">
            <div class="emoji">${getIcon(p.categoria_nome)}</div>
            ${p.categoria_nome ? `<div class="pc-category">${p.categoria_nome}</div>` : ''}
          </div>
          <div class="pc-nome" title="${p.nome}">${p.nome}</div>
          <div class="pc-details">
            <div class="pc-preco">${fmt(p.preco_venda)}</div>
            <div class="pc-estq-wrap">
              <div class="pc-estq">
                <span class="stock-dot ${stockClass}"></span>
                ${p.estoque} ${p.unidade}
              </div>
            </div>
          </div>
        </div>`;
  }).join('');
}

function addToCart(id) {
  const p = allProdutos.find(x => x.id === id); if (!p) return;
  const ex = cart.find(x => x.produto_id === id);
  if (ex) { ex.quantidade++; ex.subtotal = (ex.quantidade * (parseFloat(ex.preco_unitario) || 0)) || 0; }
  else { cart.push({ produto_id: id, produto_nome: p.nome, quantidade: 1, preco_unitario: (parseFloat(p.preco_venda) || 0), subtotal: (parseFloat(p.preco_venda) || 0), desconto: 0 }); }
  renderCart();
}
function removeFromCart(id) { cart = cart.filter(x => x.produto_id !== id); renderCart(); }
function updateQty(id, delta) { const it = cart.find(x => x.produto_id === id); if (!it) return; it.quantidade = Math.max(0.01, (parseFloat(it.quantidade) || 1) + delta); it.subtotal = (it.quantidade * (parseFloat(it.preco_unitario) || 0)) || 0; renderCart(); }
function setQty(id, val) { const it = cart.find(x => x.produto_id === id); if (!it) return; it.quantidade = Math.max(0.01, parseFloat(val) || 1); it.subtotal = (it.quantidade * (parseFloat(it.preco_unitario) || 0)) || 0; updateTotals(); }

function renderCart() {
  const el = document.getElementById('cart'); if (!el) return;
  document.getElementById('cart-count').textContent = cart.reduce((a, b) => a + b.quantidade, 0);
  if (!cart.length) { el.innerHTML = '<div class="empty"><div class="empty-icon">🛒</div><p>Carrinho vazio</p></div>'; }
  else {
    el.innerHTML = cart.map(it => `
    <div class="cart-item">
      <div class="ci-nome">${it.produto_nome}</div>
      <div class="ci-qtd">
        <button onclick="updateQty(${it.produto_id},-1)">−</button>
        <input type="number" value="${it.quantidade}" min="0.01" step="0.01" onchange="setQty(${it.produto_id},this.value)">
        <button onclick="updateQty(${it.produto_id},1)">+</button>
      </div>
      <div class="ci-sub">${fmt(it.subtotal)}</div>
      <button class="ci-rm" onclick="removeFromCart(${it.produto_id})">✕</button>
    </div>`).join('');
  }
  updateTotals();
}

function updateTotals() {
  const sub = cart.reduce((a, b) => a + (parseFloat(b.subtotal) || 0), 0);
  const desc = parseMoney(document.getElementById('cart-desconto')?.value || '0');
  const sv = document.getElementById('sub-val'); const tv = document.getElementById('total-val');
  if (sv) sv.textContent = fmt(sub); if (tv) tv.textContent = fmt(Math.max(0, sub - desc));
}

function showCheckout() {
  if (!cart.length) { notify('Carrinho vazio!', 'error'); return; }
  const sub = cart.reduce((a, b) => a + b.subtotal, 0);
  const desc = parseMoney(document.getElementById('cart-desconto')?.value || '0');
  const total = Math.max(0, sub - desc);
  const opts = allClientes.map(c => `<option value="${c.id}" data-nome="${c.nome}">${c.nome}</option>`).join('');
  const vendOpts = allVendedores.map(v => `<option value="${v.id}" data-nome="${v.nome}">${v.nome}</option>`).join('');
  const maqOpts = (window._allMaquininhas || []).map(m => `<option value="${m.id}">${m.nome}</option>`).join('');

  openModal('Finalizar Venda', `
    <div class="form-grid">
      <div class="form-group"><label>Cliente</label><select id="co-cli"><option value="">— Sem cliente —</option>${opts}</select></div>
      <div class="form-group"><label>Vendedor</label><select id="co-vend"><option value="">— Sem vendedor —</option>${vendOpts}</select></div>
      <div class="form-group">
        <label>Pagamento</label>
        <select id="co-pgto" onchange="toggleMaqSelection(this.value)">
          <option>DINHEIRO</option>
          <option>PIX</option>
          <option>CARTÃO DÉBITO</option>
          <option>CARTÃO CRÉDITO</option>
          <option>BOLETO</option>
        </select>
      </div>
      <div class="form-group" id="co-maq-wrap" style="display:none;">
        <label>Maquininha *</label>
        <select id="co-maq">
          <option value="">-- Selecione a Máquina --</option>
          ${maqOpts}
        </select>
      </div>
      <div class="form-group" id="co-parc-wrap" style="display:none;">
        <label>Parcelas</label>
        <select id="co-parc">
          <option value="1">1x (À vista)</option>
          <option value="2">2x</option>
          <option value="3">3x</option>
        </select>
      </div>
      <div class="form-group full"><label>Observação</label><input type="text" id="co-obs"></div>
      <div class="form-group full">
        <div style="background:var(--bg3);border-radius:8px;padding:14px">
          <div class="total-row"><span>Subtotal</span><span class="mono">${fmt(sub)}</span></div>
          <div class="total-row"><span>Desconto</span><span class="mono text-red">-${fmt(desc)}</span></div>
          <div class="total-row final"><span>TOTAL</span><span>${fmt(total)}</span></div>
        </div>
      </div>
    </div>
  `, `<button class="btn" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-primary" onclick="finalizarVenda()">✅ Confirmar</button>`, 'modal-md');
}

function toggleMaqSelection(val) {
  const wrap = document.getElementById('co-maq-wrap');
  const parcWrap = document.getElementById('co-parc-wrap');
  if (val.includes('CARTÃO')) {
    wrap.style.display = 'block';
    parcWrap.style.display = val.includes('CRÉDITO') ? 'block' : 'none';
  } else {
    wrap.style.display = 'none';
    parcWrap.style.display = 'none';
    document.getElementById('co-maq').value = '';
    document.getElementById('co-parc').value = '1';
  }
}

async function finalizarVenda() {
  const sub = cart.reduce((a, b) => a + (parseFloat(b.subtotal) || 0), 0);
  const desc = parseMoney(document.getElementById('cart-desconto')?.value || '0');
  const cliSel = document.getElementById('co-cli');
  const cliId = cliSel?.value || null;
  const cliNome = cliId ? cliSel.options[cliSel.selectedIndex].dataset.nome : 'Consumidor Final';
  const vendSel = document.getElementById('co-vend');
  const vendId = vendSel?.value || null;
  const vendNome = vendId ? vendSel.options[vendSel.selectedIndex].dataset.nome : '';

  const pgto = document.getElementById('co-pgto').value;
  const maqId = document.getElementById('co-maq')?.value || null;
  const numParc = document.getElementById('co-parc')?.value || 1;

  if (pgto.includes('CARTÃO') && !maqId && (window._allMaquininhas || []).length > 0) {
    notify('Selecione a maquininha usada', 'error');
    return;
  }

  const r = await api('/api/vendas', 'POST', {
    cliente_id: cliId || undefined, cliente_nome: cliNome,
    vendedor_id: vendId || undefined, vendedor_nome: vendNome,
    subtotal: sub, desconto: desc, total: Math.max(0, sub - desc),
    forma_pagamento: pgto, maquininha_id: maqId, num_parcelas: numParc,
    observacao: document.getElementById('co-obs').value, itens: cart
  });
  if (r?.ok) {
    notify(`Venda ${r.numero} concluída! 🎉`, 'success');
    const vid = r.id;
    cart = [];
    closeModal();
    allProdutos = await api('/api/produtos') || [];
    renderCart();
    renderProdutosGrid();
    document.getElementById('cart-desconto').value = '0,00';

    if (confirm('Deseja imprimir o cupom de venda?')) {
      gerarImpressaoVenda(vid);
    }
  }
  else notify('Erro ao salvar venda', 'error');
}

// ── Placeholder para continuação ────────────────────────────────
// ══════════════════════════════════════════════════════════════
// VENDAS
// ══════════════════════════════════════════════════════════════
async function renderVendas() {
  const di = today().substring(0, 7) + '-01';
  document.getElementById('content').innerHTML = `
    <div class="filters">
      <div class="filter-group"><label>Data Início</label><input type="date" id="vf-di" value="${di}"></div>
      <div class="filter-group"><label>Data Fim</label><input type="date" id="vf-df" value="${today()}"></div>
      <div class="filter-group"><label>Status</label><select id="vf-status"><option value="">Todos</option><option>CONCLUIDA</option><option>CANCELADA</option></select></div>
      <div class="filter-group"><label>Buscar</label><input type="text" id="vf-q" placeholder="Número ou cliente..."></div>
      <div style="display:flex;align-items:flex-end"><button class="btn btn-primary" onclick="loadVendas()">🔍 Filtrar</button></div>
    </div>
    <div class="card"><div class="card-header" id="vendas-resumo">💼 Vendas</div><div class="tbl-wrap" id="vendas-tbl"><div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div></div></div>`;
  loadVendas();
}

async function loadVendas() {
  const di = document.getElementById('vf-di')?.value || ''; const df = document.getElementById('vf-df')?.value || '';
  const status = document.getElementById('vf-status')?.value || ''; const q = document.getElementById('vf-q')?.value || '';
  const data = await api(`/api/vendas?data_ini=${di}&data_fim=${df}&status=${status}&q=${encodeURIComponent(q)}`);
  if (!data) return;
  const total = data.filter(v => v.status === 'CONCLUIDA').reduce((a, b) => a + b.total, 0);
  const resumo = document.getElementById('vendas-resumo');
  if (resumo) resumo.innerHTML = `💼 Vendas — <span class="text-green">${data.filter(v => v.status === 'CONCLUIDA').length} concluídas</span> | Total: <span class="mono text-green fw7">${fmt(total)}</span>`;
  const tbl = document.getElementById('vendas-tbl');
  if (!data.length) { tbl.innerHTML = '<div class="empty"><div class="empty-icon">📄</div><p>Nenhuma venda</p></div>'; return; }
  tbl.innerHTML = `<table><thead><tr><th>Número</th><th>Data</th><th>Cliente</th><th>Vendedor</th><th>Pagamento</th><th>Desconto</th><th>Total</th><th>Status</th><th></th></tr></thead>
  <tbody>${data.map(v => `<tr><td class="mono">${v.numero}</td><td>${new Date(v.criado_em).toLocaleString('pt-BR')}</td><td>${v.cliente_nome || 'Consumidor Final'}</td><td>${v.vendedor_nome || '-'}</td><td>${v.forma_pagamento}</td><td class="mono text-red">${fmt(v.desconto)}</td><td class="mono text-green fw7">${fmt(v.total)}</td><td>${badgeStatus(v.status)}</td>
  <td style="display:flex;gap:4px">
    <button class="btn btn-sm" onclick="verVenda(${v.id})">Ver</button>
    <button class="btn btn-sm" onclick="gerarImpressaoVenda(${v.id})" title="Imprimir Cupom">🖨️</button>
    ${v.status === 'CONCLUIDA' ? `<button class="btn btn-sm btn-danger" onclick="cancelarVenda(${v.id})">Cancelar</button>` : ''}
  </td></tr>`).join('')}</tbody></table>`;
}

async function verVenda(id) {
  const d = await api(`/api/vendas/${id}`); if (!d) return;
  const itens = d.itens.map(it => `<tr><td>${it.produto_nome}</td><td class="mono">${fmtN(it.quantidade)}</td><td class="mono">${fmt(it.preco_unitario)}</td><td class="mono">${fmt(it.subtotal)}</td></tr>`).join('');
  openModal(`Venda ${d.venda.numero}`, `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;font-size:13px">
      <div><span class="text-muted">Cliente:</span> ${d.venda.cliente_nome || '-'}</div>
      <div><span class="text-muted">Vendedor:</span> ${d.venda.vendedor_nome || '-'}</div>
      <div><span class="text-muted">Pagamento:</span> ${d.venda.forma_pagamento} ${d.venda.num_parcelas > 1 ? `(${d.venda.num_parcelas}x)` : ''}</div>
      <div><span class="text-muted">Data:</span> ${new Date(d.venda.criado_em).toLocaleString('pt-BR')}</div>
      ${d.venda.maquininha_id ? `<div><span class="text-muted">Taxa Operadora:</span> <span class="text-red">-${fmt(d.venda.taxa_valor)}</span></div>` : ''}
      ${d.venda.maquininha_id ? `<div><span class="text-muted">Valor Líquido:</span> <span class="text-green fw7">${fmt(d.venda.valor_liquido)}</span></div>` : ''}
      <div style="grid-column: 1 / -1;"><span class="text-muted">Status:</span> ${badgeStatus(d.venda.status)}</div>
      ${d.venda.status === 'CANCELADA' && d.venda.motivo_cancelamento ? `<div style="grid-column:1/-1;background:rgba(255,85,85,0.1);border:1px solid rgba(255,85,85,0.3);border-radius:8px;padding:10px;"><span class="text-muted">Motivo do Cancelamento:</span> <span class="text-red">${d.venda.motivo_cancelamento}</span></div>` : ''}
    </div>
    <div class="tbl-wrap"><table><thead><tr><th>Produto</th><th>Qtd</th><th>Unit.</th><th>Subtotal</th></tr></thead><tbody>${itens}</tbody></table></div>
    <div style="margin-top:12px;text-align:right">
      <span class="text-muted">Desconto: <span class="mono text-red">-${fmt(d.venda.desconto)}</span></span>&nbsp;&nbsp;
      <span style="font-size:15px;font-weight:700">Total: <span class="mono text-green">${fmt(d.venda.total)}</span></span>
    </div>
  `, `<button class="btn" onclick="gerarImpressaoVenda(${d.venda.id})">🖨️ Imprimir</button><button class="btn btn-primary" onclick="closeModal()">Fechar</button>`, 'modal-lg');
}
async function cancelarVenda(id) {
  openModal('Cancelar Venda', `
        <div class="form-grid" style="grid-template-columns:1fr">
          <div class="form-group"><label>Motivo do Cancelamento *</label><textarea id="cancel-motivo" rows="3" placeholder="Informe o motivo do cancelamento..."></textarea></div>
        </div>
      `, `<button class="btn" onclick="closeModal()">Voltar</button><button class="btn btn-danger" onclick="confirmarCancelamento(${id})">Confirmar Cancelamento</button>`, 'modal-sm');
}
async function confirmarCancelamento(id) {
  const motivo = document.getElementById('cancel-motivo')?.value.trim();
  if (!motivo) { notify('Informe o motivo do cancelamento', 'error'); return; }
  const r = await api(`/api/vendas/${id}/cancelar`, 'POST', { motivo });
  if (r?.ok) { notify('Venda cancelada', 'info'); closeModal(); loadVendas(); }
  else notify('Erro ao cancelar', 'error');
}

async function gerarImpressaoVenda(id) {
  const d = await api(`/api/vendas/${id}`); if (!d) return;
  const v = d.venda;
  const itens = d.itens;

  const html = `
      <div style="width: 72mm; margin-left: 0 auto; font-family: Arial, Helvetica, sans-serif; font-weight: 700; font-size: 12px; color: #000; padding: 5px;">
        <!-- HEADER -->
        <div style="text-align:center; margin-bottom: 5px;">
          <img src="${shopConfig.shop_logo || '/static/img/impressao.png'}" style="width: 100%; max-height: 25mm; margin-bottom: 5px; object-fit: contain;" alt="Logo" onerror="this.onerror=null;this.src='/static/img/impressao.png'">
          <div style="font-size: 10px; font-weight: bold;">${shopConfig.shop_address || '-'}</div>
          <div style="font-size: 10px; font-weight: bold;">WhatsApp: ${shopConfig.shop_whatsapp || '-'}</div>
          <div style="font-size: 10px; font-weight: bold;">Instagram: ${shopConfig.shop_instagram || '-'}</div>
        </div>
        
        <div style="border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 5px 0; text-align:center; font-weight:bold; margin-bottom: 10px;">
          CUPOM DE VENDA #${v.numero}
        </div>

        <div style="margin-bottom: 10px; font-size: 11px;">
          <b>Data:</b> ${new Date(v.criado_em).toLocaleString('pt-BR')}<br>
          <b>Cliente:</b> ${v.cliente_nome || 'Consumidor Final'}<br>
          <b>Pagamento:</b> ${v.forma_pagamento} ${v.num_parcelas > 1 ? `(${v.num_parcelas}x)` : ''}
        </div>

        <table style="width: 95%; border-collapse: collapse; font-size: 11px; margin-bottom: 10px;margin-left: 5px;margin-right: 5px; font-weight: 700;">
          <thead>
            <tr style="border-bottom: 1px solid #000;">
              <th style="text-align:left;">Item</th>
              <th style="text-align:center;">Qtd</th>
              <th style="text-align:right;">Total</th>
            </tr>
          </thead>
          <tbody>
            ${itens.map(it => `
              <tr>
                <td style="padding: 4px 0;">${it.produto_nome}</td>
                <td style="text-align:center;">${it.quantidade}</td>
                <td style="text-align:right;">${fmt(it.subtotal)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        <div style="border-top: 1px solid #000; padding-top: 5px; text-align:right; margin-right: 10px;">
          Subtotal: ${fmt(v.subtotal)}<br>
          Desconto: -${fmt(v.desconto)}<br>
          <div style="font-size: 14px; font-weight: bold; margin-top: 4px;">TOTAL: ${fmt(v.total)}</div>
        </div>

        <div style="margin-top: 20px; text-align:center; font-size: 13px; font-weight: bold;">
          Obrigado pela preferência!<br>
          Volte Sempre!
        </div>
      </div>`;

  const win = window.open('', '_blank');
  win.document.write('<html><head><title>Venda #${v.numero}</title><style>@page { margin: 0; } body { margin: 0; padding: 10px; }</style></head><body>');
  win.document.write(html);
  win.document.write('</body></html>');
  win.document.close();
  setTimeout(() => { win.print(); win.close(); }, 500);
}

function badgeStatus(s) { const m = { CONCLUIDA: 'badge-green', CANCELADA: 'badge-red', ABERTA: 'badge-blue', EM_ANDAMENTO: 'badge-orange', 'EM ANDAMENTO': 'badge-orange', AGUARDANDO: 'badge-orange', PRONTO: 'badge-purple', ENTREGUE: 'badge-gray', NORMAL: 'badge-gray', URGENTE: 'badge-red', BAIXA: 'badge-blue' }; return `<span class="badge ${m[s] || 'badge-gray'}">${s}</span>`; }

// ══════════════════════════════════════════════════════════════
// ORDENS DE SERVIÇO
// ══════════════════════════════════════════════════════════════
async function renderOS() {
  document.getElementById('topbar-actions').innerHTML = `<button class="topbar-btn primary" onclick="novaOS()">+ Nova OS</button>`;
  document.getElementById('content').innerHTML = `
    <div class="filters">
      <div class="filter-group"><label>Status</label><select id="os-status"><option value="">Todos</option><option>ABERTA</option><option>EM_ANDAMENTO</option><option>AGUARDANDO</option><option>PRONTO</option><option>CONCLUIDA</option><option>CANCELADA</option></select></div>
      <div class="filter-group"><label>Buscar</label><input type="text" id="os-q" placeholder="OS, cliente, equipamento..."></div>
      <div class="filter-group"><label>Data Início</label><input type="date" id="os-di"></div>
      <div class="filter-group"><label>Data Fim</label><input type="date" id="os-df"></div>
      <div style="display:flex;align-items:flex-end;gap:8px">
        <button class="btn btn-primary" onclick="loadOS()">🔍 Filtrar</button>
        <button class="btn" onclick="renderOSKanban()">📋 Kanban</button>
      </div>
    </div>
    <div class="card"><div class="tbl-wrap" id="os-tbl"><div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div></div></div>`;
  loadOS();
}

async function loadOS() {
  const status = document.getElementById('os-status')?.value || ''; const q = document.getElementById('os-q')?.value || '';
  const di = document.getElementById('os-di')?.value || ''; const df = document.getElementById('os-df')?.value || '';
  const data = await api(`/api/os?status=${status}&q=${encodeURIComponent(q)}&data_ini=${di}&data_fim=${df}`);
  if (!data) return;
  const tbl = document.getElementById('os-tbl');
  if (!data.length) { tbl.innerHTML = '<div class="empty"><div class="empty-icon">🔧</div><p>Nenhuma OS</p></div>'; return; }
  tbl.innerHTML = `<table><thead><tr><th>Número</th><th>Data</th><th>Cliente</th><th>Equipamento</th><th>Técnico</th><th>Prioridade</th><th>Total</th><th>Status</th><th></th></tr></thead>
  <tbody>${data.map(o => `<tr><td class="mono">${o.numero}</td><td>${new Date(o.criado_em).toLocaleDateString('pt-BR')}</td><td>${o.cliente_nome || '-'}</td><td>${o.equipamento || '-'}</td><td>${o.tecnico || '-'}</td><td>${badgeStatus(o.prioridade)}</td><td class="mono text-green">${fmt(o.total)}</td><td>${badgeStatus(o.status)}</td>
  <td style="display:flex;gap:4px"><button class="btn btn-sm" onclick="verOS(${o.id})">Ver</button><button class="btn btn-sm" onclick="editarOS(${o.id})">Editar</button></td></tr>`).join('')}</tbody></table>`;
}

async function renderOSKanban() {
  const tbl = document.getElementById('os-tbl');
  if (tbl) tbl.innerHTML = '<div class="empty"><div class="empty-icon">⏳</div><p>Carregando Kanban...</p></div>';

  const data = await api('/api/os'); if (!data) return;
  const grupos = ['ABERTA', 'EM_ANDAMENTO', 'AGUARDANDO', 'PRONTO', 'CONCLUIDA'];
  const labels = { ABERTA: 'Aberta', EM_ANDAMENTO: 'Em Andamento', AGUARDANDO: 'Aguardando', PRONTO: 'Pronto', CONCLUIDA: 'Concluída' };
  if (tbl) {
    tbl.innerHTML = `<div class="os-kanban" style="padding:14px">${grupos.map(g => `
      <div class="kanban-col"><div class="kanban-header"><span>${labels[g]}</span><span class="badge badge-blue">${data.filter(o => o.status === g).length}</span></div>
      <div class="kanban-items">${data.filter(o => o.status === g).map(o => `
        <div class="os-mini" onclick="verOS(${o.id})"><div class="om-num">${o.numero}</div><div class="om-cli">${o.cliente_nome || '-'}</div><div class="om-equip">${o.equipamento || '-'}</div></div>
      `).join('') || '<div style="font-size:12px;color:var(--text3);padding:6px">Vazio</div>'}</div></div>`).join('')}</div>`;
  }
}

async function novaOS() {
  allClientes = await api('/api/clientes') || [];
  window._os_cli_mode = 'ext'; // Default to existing client
  openModal('Nova Ordem de Serviço', buildOSForm(null), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarOS()">Salvar OS</button>`, 'modal-lg');
  setTimeout(renderPattern, 100);
}

async function editarOS(id) {
  const d = await api(`/api/os/${id}`);
  if (!d) return;
  allClientes = await api('/api/clientes') || [];
  window._os_cli_mode = 'ext'; // For edit, it's always an existing association
  openModal(`Editar OS ${d.os.numero}`, buildOSForm(d.os), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="atualizarOS(${id})">Atualizar</button>`, 'modal-lg');
  setTimeout(renderPattern, 100);
}

async function verOS(id) {
  const d = await api(`/api/os/${id}`); if (!d) return; const o = d.os;
  const ck = JSON.parse(o.checklist || '{}');
  const items = ['Aparelho Liga', 'Tela Quebrada', 'Conector Carga', 'Bateria Carga', 'Câmeras', 'Microfone', 'Auto Falante', 'Botões', 'Carcaça Boa', 'Gaveta de Chip'];
  const ckHtml = items.map(it => `<div>${ck[it] ? '✅' : '❌'} ${it}</div>`).join('');

  openModal(`OS ${o.numero}`, `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:13px">
    <div><b>Cliente:</b> ${o.cliente_nome || '-'}</div><div><b>Telefone:</b> ${o.cliente_telefone || '-'}</div>
    <div><b>Equipamento:</b> ${o.equipamento || '-'}</div><div><b>Técnico:</b> ${o.tecnico || '-'}</div>
    <div><b>Status:</b> ${badgeStatus(o.status)}</div>
    <div style="grid-column:1/-1"><b>Problema:</b> ${o.problema || '-'}</div>
    <div style="grid-column:1/-1"><b>Diagnóstico:</b> ${o.diagnostico || '-'}</div>
    <div style="grid-column:1/-1"><b>Solução:</b> ${o.solucao || '-'}</div>
    <div style="grid-column:1/-1; border-top: 1px solid var(--border); padding-top: 5px;">
      <b>Checklist:</b>
      <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-top: 5px;">${ckHtml}</div>
    </div>
    <div style="grid-column:1/-1; border-top: 1px solid var(--border); padding-top: 5px; display:flex; gap: 20px;">
      <div><b>Senha Padrão:</b> ${o.senha_padrao || '-'}</div>
      <div><b>Senha PIN:</b> ${o.senha_pin || '-'}</div>
    </div>
    <div style="grid-column:1/-1; border-top: 1px solid var(--border); padding-top: 5px;">
      <div><b>Serviço:</b> <span class="mono">${fmt(o.valor_servico)}</span></div>
      <div><b>Desconto:</b> <span class="mono text-red">-${fmt(o.desconto)}</span></div>
      <div><b>Total:</b> <span class="mono text-green fw7">${fmt(o.total)}</span></div>
    </div>
  </div>`, `<button class="btn" onclick="pedirViasOS(${o.id})">🖨️ Imprimir</button><button class="btn btn-primary" onclick="closeModal()">Fechar</button>`, 'modal-lg');
}

async function pedirViasOS(id) {
  const v = prompt("Quantas vias deseja imprimir?", "1");
  if (v) gerarImpressaoOS(id, parseInt(v) || 1);
}

async function gerarImpressaoOS(id, vias) {
  const d = await api(`/api/os/${id}`); if (!d) return; const o = d.os;
  const ck = JSON.parse(o.checklist || '{}');
  const items = ['Aparelho Liga', 'Tela Quebrada', 'Conector Carga', 'Bateria Carga', 'Câmeras', 'Microfone', 'Auto Falante', 'Botões', 'Carcaça Boa', 'Gaveta de Chip'];

  const dotsHtml = (pattern) => {
    let html = '<div style="display:grid; grid-template-columns: repeat(3, 18px); gap: 8px; width: 70px; margin: 10px 0;">';
    const p = (pattern || '').split('').map(Number);
    for (let i = 1; i <= 9; i++) {
      const idx = p.indexOf(i);
      const active = idx !== -1;
      html += `<div style="width:18px; height:18px; border-radius:50%; border:2px solid #000; display:flex; align-items:center; justify-content:center; position:relative; font-size:9px;">
            ${active ? '<div style="width:7px; height:7px; background:#000; border-radius:50%;"></div>' : ''}
            ${active ? `<span style="position:absolute; top:-5px; right:-5px; font-weight:bold;">${idx + 1}</span>` : ''}
          </div>`;
    }
    return html + '</div>';
  };

  let html = '';
  const viaHtml = `
      <div style="width: 72mm; margin: 0 auto; font-family: Arial, Helvetica, sans-serif; font-weight: 700; font-size: 12px; color: #000; padding: 5px; border-bottom: 1px dashed #000; margin-bottom: 10mm;">
        <!-- HEADER -->
        <div style="text-align:center; margin-bottom: 5px;">
          <img src="${shopConfig.shop_logo || '/static/img/impressao.png'}" style="width: 100%; max-height: 25mm; margin-bottom: 5px; object-fit: contain;" alt="Logo" onerror="this.onerror=null;this.src='/static/img/impressao.png'">
          <div style="font-size: 10px;font-weight: bold;">${shopConfig.shop_address || '-'}</div>
          <div style="font-size: 10px;font-weight: bold;">WhatsApp: ${shopConfig.shop_whatsapp || '-'}</div>
          <div style="font-size: 10px;font-weight: bold;">Instagram: ${shopConfig.shop_instagram || '-'}</div>
        </div>
        
        <div style="border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 5px 0; text-align:center; font-weight:bold;">
          ORDEM DE SERVIÇO #${o.numero}
        </div>

        <div style="margin: 10px 0;">
          <b>Data:</b> ${new Date(o.criado_em).toLocaleDateString('pt-BR')}<br>
          <b>Cliente:</b> ${(o.cliente_nome || '-').substring(0, 30)}<br>
          <b>Telefone:</b> ${o.cliente_telefone || '-'}<br>
          <b>Equipamento:</b> ${o.equipamento || '-'}<br>
          <b>Técnico:</b> ${o.tecnico || '-'}<br>
          <b>Status:</b> ${o.status}
        </div>

        <div style="border-top: 1px dashed #ccc; padding-top: 5px; margin-bottom: 5px;">
          <b>Problema:</b> ${o.problema || '-'}
        </div>

        <div style="border-top: 1px dashed #ccc; padding-top: 5px; margin-bottom: 5px;">
          <b>CHECKLIST:</b>
          <div style="display:grid; grid-template-columns: 1fr 1fr; font-size: 10px; margin-top:2px;">
            ${items.map(it => `<div>[${ck[it] ? '✓' : 'X'}] ${it}</div>`).join('')}
          </div>
        </div>

        <div style="border-top: 1px dashed #ccc; padding-top: 5px; margin-bottom: 5px; display:flex; justify-content:flex-start; gap:110px; align-items:center;">
          <div>
            <b>Senhas:</b><br>
            PIN: ${o.senha_pin || '-'}<br>
            Padrão: ${o.senha_padrao || '-'}
          </div>
          <div style="text-align:center;">
            ${o.senha_padrao ? dotsHtml(o.senha_padrao) : ''}
          </div>
        </div>

        <div style="border-top: 1px solid #000; padding-top: 5px; margin-top: 5px; text-align:right;margin-right:10px;">
          Serviço: ${fmt(o.valor_servico)}<br>
          Desconto: -${fmt(o.desconto)}<br>
          <span style="font-size: 14px; font-weight: bold;">TOTAL: ${fmt(o.total)}</span>
        </div>

        <div style="margin-top: 20px; text-align:center; font-size: 13px;font-weight: bold;">
          _________________________________<br>
          Assinatura do Cliente
        </div>
        <div style="text-align:center; font-size: 10px; margin-top: 10px; color: #666;font-weight: bold;">
          Obrigado pela preferência!
        </div>
      </div>`;

  for (let i = 0; i < vias; i++) html += viaHtml;

  const win = window.open('', '_blank');
  win.document.write('<html><head><title>OS #${o.numero}</title><style>@page { margin: 0; } body { margin: 0; padding: 0; }</style></head><body>');
  win.document.write(html);
  win.document.write('</body></html>');
  win.document.close();
  setTimeout(() => { win.print(); win.close(); }, 500);
}

function buildOSForm(o) {
  const cliOpts = allClientes.map(c => `<option value="${c.id}" ${o && o.cliente_id == c.id ? 'selected' : ''}>${c.nome}</option>`).join('');
  const vsVal = o ? fmtN(o.valor_servico) : '0,00';
  const descVal = o ? fmtN(o.desconto) : '0,00';
  const ck = JSON.parse(o?.checklist || '{}');
  const items = ['Aparelho Liga', 'Tela Quebrada', 'Conector Carga', 'Bateria Carga', 'Câmeras', 'Microfone', 'Auto Falante', 'Botões', 'Carcaça Boa', 'Gaveta de Chip'];

  const ckHtml = items.map(it => `
        <div class="ck-chip ${ck[it] ? 'active' : ''}" onclick="toggleCkChip(this)">
          <input type="checkbox" class="os-ck" data-item="${it}" ${ck[it] ? 'checked' : ''}>
          <div class="chip-icon">${ck[it] ? '✓' : ''}</div>
          <span>${it}</span>
        </div>
      `).join('');

  let dotsHtml = '<div class="pattern-grid" id="os-pattern-grid" style="margin: 0 auto;">';
  for (let i = 1; i <= 9; i++) dotsHtml += `<div class="p-dot" data-idx="${i}" onclick="togglePatternPoint(${i})"></div>`;
  dotsHtml += '</div>';

  return `
      <div class="form-tabs">
        <button class="tab-btn active" onclick="switchOSTab(0)">📱 Identificação</button>
        <button class="tab-btn" onclick="switchOSTab(1)">🔍 Diagnóstico</button>
        <button class="tab-btn" onclick="switchOSTab(2)">🛠️ Execução</button>
        <button class="tab-btn" onclick="switchOSTab(3)">💰 Finalização</button>
      </div>

      <!-- TAB 0: IDENTIFICAÇÃO -->
      <div class="form-tab-content active" id="os-tab-0">
        <div class="glass-card">
          <div class="form-group" style="margin-bottom:20px">
            <label>Buscar Cliente (Opcional)</label>
            <select id="os-cli" onchange="onOSClientChange(this.value)">
              <option value="">— Selecionar Cliente Existente ou Deixar Vazio para Novo —</option>
              ${cliOpts}
            </select>
          </div>

          <div class="form-grid cols3">
            <div class="form-group"><label>Nome Completo *</label><input id="os-nc-nome" value="${o?.cliente_nome || ''}" placeholder="Nome do cliente"></div>
            <div class="form-group"><label>CPF / CNPJ</label><input id="os-nc-doc" value="${o?.cliente_cpf || ''}" placeholder="000.000.000-00"></div>
            <div class="form-group"><label>Telefone</label><input id="os-nc-tel" value="${o?.cliente_telefone || ''}" placeholder="(11) 99999-9999"></div>
          </div>

          <div class="form-group" style="margin-top:15px"><label>Equipamento / Modelo</label><input id="os-equip" value="${o?.equipamento || ''}" placeholder="Ex: iPhone 13 Pro Max"></div>
          
          <div class="form-grid" style="grid-template-columns: 1fr 2fr; gap: 20px; margin-top: 15px;">
            <div class="form-group" style="text-align:center; background: var(--bg2); padding: 15px; border-radius: 12px; border: 1px solid var(--border);">
              <label style="margin-bottom: 12px; font-weight: 600;">Senha Padrão (Desenho)</label>
              ${dotsHtml}
              <input type="hidden" id="os-spad" value="${o?.senha_padrao || ''}">
              <button class="btn btn-sm" onclick="clearPattern()" style="margin-top:10px; width: 100%;">Limpar</button>
            </div>
            <div class="form-group">
              <label>Senha PIN / Texto</label>
              <input id="os-spin" value="${o?.senha_pin || ''}" placeholder="Caso não seja padrão de desenho" style="height: 48px; font-size: 16px;">
              <div style="margin-top: 20px;">
                <label>Responsável / Técnico</label>
                <input id="os-tec" value="${o?.tecnico || ''}" placeholder="Nome do técnico responsável">
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 1: DIAGNÓSTICO -->
      <div class="form-tab-content" id="os-tab-1">
        <div class="glass-card">
          <label style="display:block; margin-bottom: 15px; font-weight: 600; color: var(--blue);">CHECKLIST DE ENTRADA</label>
          <div class="ck-chip-grid">${ckHtml}</div>
        </div>
        <div class="glass-card">
          <label style="display:block; margin-bottom: 10px; font-weight: 600;">PROBLEMA RELATADO PELO CLIENTE</label>
          <textarea id="os-prob" rows="4" style="font-size:14px" placeholder="Descreva detalhadamente o que o cliente informou...">${o?.problema || ''}</textarea>
        </div>
      </div>

      <!-- TAB 2: EXECUÇÃO -->
      <div class="form-tab-content" id="os-tab-2">
        <div class="glass-card">
          <label style="display:block; margin-bottom: 10px; font-weight: 600;">DIAGNÓSTICO TÉCNICO (INTERNO)</label>
          <textarea id="os-diag" rows="4" style="font-size:14px" placeholder="O que foi constatado após a análise técnico...">${o?.diagnostico || ''}</textarea>
        </div>
        <div class="glass-card">
          <label style="display:block; margin-bottom: 10px; font-weight: 600; color: var(--green);">SOLUÇÃO EFETUADA</label>
          <textarea id="os-sol" rows="4" style="font-size:14px" placeholder="Descreva as peças trocadas e serviços realizados...">${o?.solucao || ''}</textarea>
        </div>
      </div>

      <!-- TAB 3: FINALIZAÇÃO -->
      <div class="form-tab-content" id="os-tab-3">
        <div class="glass-card">
          <div class="form-grid cols3">
            <div class="form-group"><label>Status O.S.</label><select id="os-st" style="height: 42px; font-weight: 600;">${['ABERTA', 'EM_ANDAMENTO', 'AGUARDANDO', 'PRONTO', 'CONCLUIDA', 'CANCELADA'].map(s => `<option ${o?.status === s ? 'selected' : ''} value="${s}">${s}</option>`).join('')}</select></div>
            <div class="form-group"><label>Prioridade</label><select id="os-pri" style="height: 42px;">${['NORMAL', 'URGENTE', 'BAIXA'].map(s => `<option ${o?.prioridade === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div>
            <div class="form-group"><label>Previsão</label><input type="date" id="os-prev" value="${o?.previsao || ''}" style="height: 42px;"></div>
          </div>
        </div>
        <div class="glass-card">
          <div class="form-grid cols3">
            <div class="form-group"><label>Forma de Pagamento</label><select id="os-pgto">${['DINHEIRO', 'PIX', 'CARTÃO DÉBITO', 'CARTÃO CRÉDITO'].map(s => `<option ${o?.forma_pagamento === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div>
            <div class="form-group"><label>Valor Serviço</label><input type="text" id="os-vs" value="${vsVal}" oninput="this.value=maskMoney(this.value);calcOsTotal()" style="font-size: 18px; font-weight: 700; color: var(--blue);"></div>
            <div class="form-group"><label>Desconto</label><input type="text" id="os-desc" value="${descVal}" oninput="this.value=maskMoney(this.value);calcOsTotal()" style="font-size: 18px; font-weight: 700; color: var(--red);"></div>
          </div>
          <div style="margin-top: 20px; padding: 20px; background: rgba(63, 185, 80, 0.1); border-radius: 12px; border: 1px solid rgba(63, 185, 80, 0.2); text-align: center;">
            <div style="font-size: 12px; color: var(--text2); text-transform: uppercase; letter-spacing: 1px;">Valor Total a Pagar</div>
            <input type="text" id="os-tot" readonly style="font-size: 32px; font-weight: 800; color: var(--green); background: transparent; border: none; text-align: center; width: 100%; outline: none;">
          </div>
        </div>
        <div class="form-group full"><label>Observações Internas (Não saem na impressão)</label><input id="os-obs" value="${o?.observacao || ''}" placeholder="Notas extras..."></div>
      </div>`;
}

function switchOSTab(idx) {
  document.querySelectorAll('#modal-body .tab-btn').forEach((b, i) => b.classList.toggle('active', i === idx));
  document.querySelectorAll('#modal-body .form-tab-content').forEach((c, i) => c.classList.toggle('active', i === idx));
}

function toggleCkChip(el) {
  el.classList.toggle('active');
  const cb = el.querySelector('input');
  if (cb) { cb.checked = el.classList.contains('active'); }
  const icon = el.querySelector('.chip-icon');
  if (icon) icon.textContent = cb.checked ? '✓' : '';
}

async function onOSClientChange(id) {
  if (!id) return;
  const c = allClientes.find(x => x.id == id);
  if (c) {
    const nomeInput = document.getElementById('os-nc-nome');
    const docInput = document.getElementById('os-nc-doc');
    const telInput = document.getElementById('os-nc-tel');
    if (nomeInput) nomeInput.value = c.nome;
    if (docInput) docInput.value = c.cpf_cnpj || '';
    if (telInput) telInput.value = c.telefone || '';
  }
}

// Pattern dots logic
let currentPattern = [];
function togglePatternPoint(idx) {
  const dot = document.querySelector(`.p-dot[data-idx="${idx}"]`);
  if (!dot) return;
  const pos = currentPattern.indexOf(idx);
  if (pos === -1) {
    currentPattern.push(idx); dot.classList.add('active');
    const badge = document.createElement('div'); badge.className = 'p-badge';
    badge.textContent = currentPattern.length; dot.appendChild(badge);
  } else {
    // Only allow removing the last one to maintain sequence, or clear all
    if (pos === currentPattern.length - 1) {
      currentPattern.pop(); dot.classList.remove('active');
      const b = dot.querySelector('.p-badge'); if (b) b.remove();
    }
  }
  document.getElementById('os-spad').value = currentPattern.join('');
}
function clearPattern() {
  currentPattern = [];
  document.querySelectorAll('.p-dot').forEach(d => { d.classList.remove('active'); const b = d.querySelector('.p-badge'); if (b) b.remove(); });
  document.getElementById('os-spad').value = '';
}
function renderPattern() {
  const val = document.getElementById('os-spad')?.value || '';
  clearPattern();
  if (val) { val.split('').forEach(v => togglePatternPoint(parseInt(v))); }
}

function calcOsTotal() {
  const vs = parseMoney(document.getElementById('os-vs')?.value || '0');
  const desc = parseMoney(document.getElementById('os-desc')?.value || '0');
  const tot = Math.max(0, vs - desc);
  const el = document.getElementById('os-tot');
  if (el) el.value = fmt(tot);
}

async function salvarOS() {
  const vs = parseMoney(document.getElementById('os-vs')?.value || '0');
  const desc = parseMoney(document.getElementById('os-desc')?.value || '0');
  const ck = {}; document.querySelectorAll('.os-ck').forEach(el => { ck[el.dataset.item] = el.checked; });
  const cliId = document.getElementById('os-cli').value;

  const payload = {
    cliente_id: cliId || null,
    cliente_nome: document.getElementById('os-nc-nome').value,
    cliente_cpf: document.getElementById('os-nc-doc').value,
    cliente_telefone: document.getElementById('os-nc-tel').value,
    equipamento: document.getElementById('os-equip').value,
    tecnico: document.getElementById('os-tec').value,
    problema: document.getElementById('os-prob').value,
    diagnostico: document.getElementById('os-diag').value,
    solucao: document.getElementById('os-sol').value,
    status: document.getElementById('os-st').value,
    prioridade: document.getElementById('os-pri').value,
    previsao: document.getElementById('os-prev').value,
    forma_pagamento: document.getElementById('os-pgto').value,
    valor_servico: vs, desconto: desc, total: vs - desc,
    senha_padrao: document.getElementById('os-spad').value,
    senha_pin: document.getElementById('os-spin').value,
    observacao: document.getElementById('os-obs').value,
    checklist: JSON.stringify(ck)
  };

  const r = await api('/api/os', 'POST', payload);
  if (r?.ok) { notify('OS Criada!', 'success'); closeModal(); loadOS(); }
  else notify('Erro ao salvar', 'error');
}

async function atualizarOS(id) {
  const vs = parseMoney(document.getElementById('os-vs')?.value || '0');
  const desc = parseMoney(document.getElementById('os-desc')?.value || '0');
  const ck = {}; document.querySelectorAll('.os-ck').forEach(el => { ck[el.dataset.item] = el.checked; });
  const payload = {
    equipamento: document.getElementById('os-equip').value,
    tecnico: document.getElementById('os-tec').value,
    problema: document.getElementById('os-prob').value,
    diagnostico: document.getElementById('os-diag').value,
    solucao: document.getElementById('os-sol').value,
    status: document.getElementById('os-st').value,
    prioridade: document.getElementById('os-pri').value,
    previsao: document.getElementById('os-prev').value,
    forma_pagamento: document.getElementById('os-pgto').value,
    valor_servico: vs, desconto: desc, total: vs - desc,
    senha_padrao: document.getElementById('os-spad').value,
    senha_pin: document.getElementById('os-spin').value,
    observacao: document.getElementById('os-obs').value,
    checklist: JSON.stringify(ck)
  };
  const r = await api(`/api/os/${id}`, 'PUT', payload);
  if (r?.ok) { notify('OS Atualizada!', 'success'); closeModal(); loadOS(); }
  else notify('Erro ao atualizar', 'error');
}


// ══════════════════════════════════════════════════════════════
// PRODUTOS
// ══════════════════════════════════════════════════════════════
function gerarCodigo() {
  const code = Math.floor(1000000000 + Math.random() * 9000000000).toString();
  const input = document.getElementById('pf-cod');
  if (input) {
    input.value = code;
    notify('Código gerado!', 'success');
  }
}

async function renderProdutos() {
  allCategorias = await api('/api/categorias') || [];
  
  // Build hierarchical category options for the filter
  const pais = allCategorias.filter(c => !c.pai_id);
  let catFilterOpts = '';
  pais.forEach(pai => {
    catFilterOpts += `<option value="${pai.id}">${pai.nome}</option>`;
    const subs = allCategorias.filter(c => c.pai_id == pai.id);
    subs.forEach(sub => {
      catFilterOpts += `<option value="${sub.id}">&nbsp;&nbsp;&nbsp;↳ ${sub.nome}</option>`;
    });
  });

  document.getElementById('topbar-actions').innerHTML = `
        <button class="topbar-btn" onclick="renderCategorias()">📁 Categorias</button>
        <button class="topbar-btn primary" onclick="novoProduto()">+ Novo Produto</button>
      `;
  document.getElementById('content').innerHTML = `
    <div class="filters">
      <div class="filter-group"><label>Categoria</label><select id="pf-cat"><option value="">Todas</option>${catFilterOpts}</select></div>
      <div class="filter-group"><label>Estoque</label><select id="pf-estq"><option value="">Todos</option><option value="baixo">Baixo (<= Min)</option><option value="zero">Zerado</option></select></div>
      <div class="filter-group"><label>Buscar</label><input type="text" id="pf-q" placeholder="Nome ou código..."></div>
      <div style="display:flex;align-items:flex-end"><button class="btn btn-primary" onclick="loadProdutos()">🔍 Filtrar</button></div>
    </div>
    <div class="card"><div class="tbl-wrap" id="prod-tbl"><div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div></div></div>`;
  loadProdutos();
}

async function loadProdutos() {
  const cat = document.getElementById('pf-cat')?.value || ''; const estq = document.getElementById('pf-estq')?.value || '';
  const q = document.getElementById('pf-q')?.value || '';
  const data = await api(`/api/produtos?categoria_id=${cat}&estoque=${estq}&q=${encodeURIComponent(q)}`);
  if (!data) return;
  allProdutos = data;
  const tbl = document.getElementById('prod-tbl');
  if (!data.length) { tbl.innerHTML = '<div class="empty"><div class="empty-icon">📦</div><p>Nenhum produto</p></div>'; return; }
  tbl.innerHTML = `<table><thead><tr><th>Código</th><th>Nome</th><th>Categoria</th><th>Estoque</th><th>Custo</th><th>Venda</th><th>Lucro</th><th></th></tr></thead>
  <tbody>${data.map(p => {
    const lucro = (p.preco_venda - p.preco_custo);
    const margem = p.preco_custo > 0 ? (lucro / p.preco_custo * 100).toFixed(1) : '---';
    const stClass = p.estoque <= 0 ? 'text-red fw7' : (p.estoque <= p.estoque_minimo ? 'text-orange fw7' : '');
    return `<tr><td class="mono">${p.codigo || '-'}</td><td>${p.nome}</td><td>${p.categoria_nome || '-'}</td><td class="${stClass}">${p.estoque} ${p.unidade}</td><td class="mono">${fmt(p.preco_custo)}</td><td class="mono fw7 text-blue">${fmt(p.preco_venda)}</td><td class="mono text-green">${fmt(lucro)} <small>(${margem}%)</small></td>
  <td style="display:flex;gap:4px"><button class="btn btn-sm" onclick="editarProduto(${p.id})">Editar</button><button class="btn btn-sm btn-danger" onclick="deletarProduto(${p.id})">🗑️</button></td></tr>`;
  }).join('')}</tbody></table>`;
}

function buildProdForm(p) {
  // Agrupa categorias e subcategorias para o select
  const pais = allCategorias.filter(c => !c.pai_id);
  let catOpts = '';
  pais.forEach(pai => {
    catOpts += `<option value="${pai.id}" ${p && p.categoria_id == pai.id ? 'selected' : ''}>${pai.nome}</option>`;
    const subs = allCategorias.filter(c => c.pai_id == pai.id);
    subs.forEach(sub => {
      catOpts += `<option value="${sub.id}" ${p && p.categoria_id == sub.id ? 'selected' : ''}>&nbsp;&nbsp;&nbsp;↳ ${sub.nome}</option>`;
    });
  });
  // Adiciona órfãs (caso existam por algum erro de integridade ou lógica)
  allCategorias.filter(c => c.pai_id && !allCategorias.find(pd => pd.id == c.pai_id)).forEach(c => {
    catOpts += `<option value="${c.id}" ${p && p.categoria_id == c.id ? 'selected' : ''}>${c.nome} (S/ Pai)</option>`;
  });

  return `
    <div class="form-grid">
      <div class="form-group full"><label>Nome do Produto *</label><input id="pf-nome" value="${p?.nome || ''}" placeholder="Ex: Película 3D iPhone 13"></div>
      <div class="form-group">
        <label>Código / SKU</label>
        <div style="display:flex;gap:4px">
          <input id="pf-cod" value="${p?.codigo || ''}" placeholder="OPCIONAL" style="flex:1">
          <button type="button" class="btn btn-sm" onclick="gerarCodigo()" title="Gerar Código Aleatório">⚡</button>
        </div>
      </div>
      <div class="form-group"><label>Categoria</label><select id="pf-cat-id"><option value="">— Sem Categoria —</option>${catOpts}</select></div>
      <div class="form-group"><label>Preço Custo</label><input id="pf-pc" value="${p ? fmtN(p.preco_custo) : '0,00'}" oninput="this.value=maskMoney(this.value)"></div>
      <div class="form-group"><label>Preço Venda *</label><input id="pf-pv" value="${p ? fmtN(p.preco_venda) : '0,00'}" oninput="this.value=maskMoney(this.value)"></div>
      <div class="form-group"><label>Estoque Atual</label><input type="number" id="pf-est" value="${p?.estoque || 0}"></div>
      <div class="form-group"><label>Estoque Mínimo</label><input type="number" id="pf-min" value="${p?.estoque_minimo || 0}"></div>
      <div class="form-group"><label>Unidade</label><input id="pf-uni" value="${p?.unidade || 'un'}" placeholder="Ex: un, par, m"></div>
      <div class="form-group full"><label>URL da Imagem</label><input id="pf-img" value="${p?.imagem_url || ''}" placeholder="http://..."></div>
    </div>`;
}
async function novoProduto() { openModal('Novo Produto', buildProdForm(), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarProduto()">Criar</button>`); }
async function editarProduto(id) { const p = allProdutos.find(x => x.id === id); openModal('Editar Produto', buildProdForm(p), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarProduto(${id})">Salvar</button>`); }
async function salvarProduto(id = null) {
  const body = {
    nome: document.getElementById('pf-nome').value, 
    codigo: document.getElementById('pf-cod').value,
    categoria_id: document.getElementById('pf-cat-id').value || null, 
    preco_custo: parseMoney(document.getElementById('pf-pc').value),
    preco_venda: parseMoney(document.getElementById('pf-pv').value), 
    estoque: parseFloat(document.getElementById('pf-est').value || 0),
    estoque_minimo: parseFloat(document.getElementById('pf-min').value || 0), 
    unidade: document.getElementById('pf-uni').value,
    imagem_url: document.getElementById('pf-img')?.value || null
  };
  if (!body.nome || !body.preco_venda) { notify('Nome e Preço de Venda são obrigatórios', 'error'); return; }
  const r = id ? await api(`/api/produtos/${id}`, 'PUT', body) : await api('/api/produtos', 'POST', body);
  if (r?.ok) { notify('Produto salvo!'); closeModal(); loadProdutos(); }
  else notify('Erro ao salvar', 'error');
}
async function deletarProduto(id) { if (!confirm('Deseja excluir este produto?')) return; const r = await api(`/api/produtos/${id}`, 'DELETE'); if (r?.ok) { notify('Excluído'); loadProdutos(); } }

// ── Categorias ─────────────────────────────────────────────────
async function renderCategorias() {
  allCategorias = await api('/api/categorias') || [];
  document.getElementById('page-title').textContent = 'Gerenciar Categorias';
  document.getElementById('topbar-actions').innerHTML = `
        <button class="topbar-btn" onclick="navigate('produtos')">⬅ Voltar</button>
        <button class="topbar-btn primary" onclick="novaCategoria()">+ Nova Categoria</button>
      `;
  document.getElementById('content').innerHTML = `
        <div class="card"><div class="tbl-wrap" id="cat-tbl">
          <div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div>
        </div></div>`;
  loadCategoriasList();
}

function loadCategoriasList() {
  const tbl = document.getElementById('cat-tbl');
  if (!allCategorias.length) { tbl.innerHTML = '<div class="empty"><div class="empty-icon">📁</div><p>Nenhuma categoria</p></div>'; return; }

  // Organiza por árvore
  const pais = allCategorias.filter(c => !c.pai_id);
  let rows = '';

  pais.forEach(pai => {
    rows += `<tr><td class="fw7">${pai.nome}</td><td>—</td>
          <td style="display:flex;gap:4px">
            <button class="btn btn-sm" onclick="editarCategoria(${pai.id})">Editar</button>
            <button class="btn btn-sm btn-danger" onclick="deletarCategoria(${pai.id})">🗑️</button>
          </td></tr>`;

    const subs = allCategorias.filter(c => c.pai_id == pai.id);
    subs.forEach(sub => {
      rows += `<tr class="cat-row-sub"><td>↳ ${sub.nome}</td><td><span class="cat-pai-badge">Sub de: ${pai.nome}</span></td>
          <td style="display:flex;gap:4px">
            <button class="btn btn-sm" onclick="editarCategoria(${sub.id})">Editar</button>
            <button class="btn btn-sm btn-danger" onclick="deletarCategoria(${sub.id})">🗑️</button>
          </td></tr>`;
    });
  });

  tbl.innerHTML = `<table><thead><tr><th>Nome</th><th>Pai</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;
}

function buildCatForm(c) {
  const pais = allCategorias.filter(cat => !cat.pai_id && (!c || cat.id != c.id));
  const catOpts = pais.map(p => `<option value="${p.id}" ${c && c.pai_id == p.id ? 'selected' : ''}>${p.nome}</option>`).join('');
  return `
        <div class="form-grid" style="grid-template-columns:1fr">
          <div class="form-group"><label>Nome da Categoria *</label><input id="cat-nome" value="${c?.nome || ''}" placeholder="Ex: Acessórios"></div>
          <div class="form-group"><label>Categoria Pai (Opcional)</label><select id="cat-pai-id"><option value="">— Nenhuma / Categoria Principal —</option>${catOpts}</select></div>
        </div>`;
}

function novaCategoria() {
  openModal('Nova Categoria', buildCatForm(), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarCategoria()">Criar</button>`, 'modal-sm');
}

function editarCategoria(id) {
  const c = allCategorias.find(x => x.id === id);
  openModal('Editar Categoria', buildCatForm(c), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarCategoria(${id})">Salvar</button>`, 'modal-sm');
}

async function salvarCategoria(id = null) {
  const body = {
    nome: document.getElementById('cat-nome').value,
    pai_id: document.getElementById('cat-pai-id').value || null
  };
  if (!body.nome) { notify('Nome é obrigatório', 'error'); return; }
  const r = id ? await api(`/api/categorias/${id}`, 'PUT', body) : await api('/api/categorias', 'POST', body);
  if (r?.ok) { notify('Categoria salva!'); closeModal(); renderCategorias(); }
  else notify(r?.message || 'Erro ao salvar', 'error');
}

async function deletarCategoria(id) {
  if (!confirm('Deseja excluir esta categoria? Isso também excluirá subcategorias vinculadas.')) return;
  const r = await api(`/api/categorias/${id}`, 'DELETE');
  if (r?.ok) { notify('Excluída'); renderCategorias(); }
  else notify(r?.message || 'Erro ao excluir', 'error');
}

// ══════════════════════════════════════════════════════════════
// CLIENTES
// ══════════════════════════════════════════════════════════════
async function renderClientes() {
  document.getElementById('topbar-actions').innerHTML = `<button class="topbar-btn primary" onclick="novoCliente()">+ Novo Cliente</button>`;
  document.getElementById('content').innerHTML = `
    <div class="filters">
      <div class="filter-group" style="flex:1"><label>Buscar</label><input type="text" id="cf-q" placeholder="Nome, CPF, Telefone..." oninput="loadClientes()"></div>
      <div style="display:flex;align-items:flex-end"><button class="btn btn-primary" onclick="loadClientes()">🔍 Filtrar</button></div>
    </div>
    <div class="card"><div class="tbl-wrap" id="cli-tbl"><div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div></div></div>`;
  loadClientes();
}
async function loadClientes() {
  const q = document.getElementById('cf-q')?.value || '';
  const data = await api(`/api/clientes?q=${encodeURIComponent(q)}`);
  if (!data) return;
  allClientes = data;
  const tbl = document.getElementById('cli-tbl');
  if (!data.length) { tbl.innerHTML = '<div class="empty"><div class="empty-icon">👥</div><p>Nenhum cliente</p></div>'; return; }
  tbl.innerHTML = `<table><thead><tr><th>Nome</th><th>CPF/CNPJ</th><th>Telefone</th><th>Email</th><th>Cidade</th><th></th></tr></thead>
  <tbody>${data.map(c => `<tr><td class="fw7">${c.nome}</td><td class="mono">${c.cpf_cnpj || '-'}</td><td>${c.telefone || '-'}</td><td>${c.email || '-'}</td><td>${c.cidade || '-'}</td>
  <td style="display:flex;gap:4px"><button class="btn btn-sm" onclick="editarCliente(${c.id})">Editar</button><button class="btn btn-sm btn-danger" onclick="deletarCliente(${c.id})">🗑️</button></td></tr>`).join('')}</tbody></table>`;
}
function buildCliForm(c) {
  return `
    <div class="form-grid">
      <div class="form-group full"><label>Nome / Razão Social *</label><input id="cf-nome" value="${c?.nome || ''}"></div>
      <div class="form-group"><label>CPF / CNPJ</label><input id="cf-doc" value="${c?.cpf_cnpj || ''}"></div>
      <div class="form-group"><label>Telefone</label><input id="cf-tel" value="${c?.telefone || ''}"></div>
      <div class="form-group"><label>E-mail</label><input type="email" id="cf-email" value="${c?.email || ''}"></div>
      <div class="form-group"><label>CEP</label><input id="cf-cep" value="${c?.cep || ''}"></div>
      <div class="form-group full"><label>Endereço</label><input id="cf-end" value="${c?.endereco || ''}"></div>
      <div class="form-group"><label>Cidade</label><input id="cf-cid" value="${c?.cidade || ''}"></div>
      <div class="form-group"><label>Bairro</label><input id="cf-bai" value="${c?.bairro || ''}"></div>
    </div>`;
}
async function novoCliente() { openModal('Novo Cliente', buildCliForm(), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarCliente()">Criar</button>`); }
async function editarCliente(id) { const c = allClientes.find(x => x.id === id); openModal('Editar Cliente', buildCliForm(c), `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarCliente(${id})">Salvar</button>`); }
async function salvarCliente(id = null) {
  const body = {
    nome: document.getElementById('cf-nome').value, cpf_cnpj: document.getElementById('cf-doc').value,
    telefone: document.getElementById('cf-tel').value, email: document.getElementById('cf-email').value,
    cep: document.getElementById('cf-cep').value, endereco: document.getElementById('cf-end').value,
    cidade: document.getElementById('cf-cid').value, bairro: document.getElementById('cf-bai').value
  };
  if (!body.nome) { notify('Nome é obrigatório', 'error'); return; }
  const r = id ? await api(`/api/clientes/${id}`, 'PUT', body) : await api('/api/clientes', 'POST', body);
  if (r?.ok) { notify('Cliente salvo!'); closeModal(); loadClientes(); }
  else notify('Erro ao salvar', 'error');
}
async function deletarCliente(id) { if (!confirm('Deseja excluir este cliente?')) return; const r = await api(`/api/clientes/${id}`, 'DELETE'); if (r?.ok) { notify('Excluído'); loadClientes(); } }

// ══════════════════════════════════════════════════════════════
// FINANCEIRO
// ══════════════════════════════════════════════════════════════
async function renderFinanceiro() {
  // If we directly navigated to 'receber', init with that tab
  const initialTab = (currentPage === 'receber') ? 'receber' : 'fluxo';

  document.getElementById('topbar-actions').innerHTML = `
    <div class="tab-pill">
      <button class="pill-btn ${initialTab === 'fluxo' ? 'active' : ''}" onclick="switchFinTab('fluxo')">💸 Fluxo de Caixa</button>
      <button class="pill-btn ${initialTab === 'receber' ? 'active' : ''}" onclick="switchFinTab('receber')">📅 Contas a Receber</button>
    </div>
  `;
  document.getElementById('content').innerHTML = `<div id="fin-content"></div>`;
  switchFinTab(initialTab);
}

function switchFinTab(tab) {
  document.querySelectorAll('.pill-btn').forEach(b => b.classList.toggle('active', b.onclick.toString().includes(`'${tab}'`)));
  if (tab === 'fluxo') renderFluxo(); else renderReceber();
}

async function renderFluxo() {
  const di = firstDay(); const df = today();
  document.getElementById('fin-content').innerHTML = `
    <div class="filters">
      <div class="filter-group"><label>Início</label><input type="date" id="ff-di" value="${di}"></div>
      <div class="filter-group"><label>Fim</label><input type="date" id="ff-df" value="${df}"></div>
      <div style="display:flex;align-items:flex-end;gap:8px">
        <button class="btn btn-primary" onclick="loadFluxo()">🔍 Filtrar</button>
        <button class="btn btn-danger" onclick="novaDespesa()">+ Despesa</button>
      </div>
    </div>
    <div id="fluxo-resumo" class="stats-grid" style="margin-bottom:20px"></div>
    <div class="card"><div class="card-header">Movimentações</div><div class="tbl-wrap" id="fluxo-tbl"></div></div>`;
  loadFluxo();
}

async function loadFluxo() {
  const di = document.getElementById('ff-di').value; const df = document.getElementById('ff-df').value;
  const d = await api(`/api/financeiro/fluxo?data_ini=${di}&data_fim=${df}`);
  if (!d) return;
  document.getElementById('fluxo-resumo').innerHTML = `
    <div class="stat-card blue"><div class="stat-label">Entradas</div><div class="stat-value">${fmt(d.entradas)}</div></div>
    <div class="stat-card red"><div class="stat-label">Saídas (Despesas)</div><div class="stat-value">${fmt(d.saidas)}</div></div>
    <div class="stat-card ${d.saldo >= 0 ? 'green' : 'red'}"><div class="stat-label">Saldo Período</div><div class="stat-value">${fmt(d.saldo)}</div></div>
  `;
  const tbl = document.getElementById('fluxo-tbl');
  if (!d.movimentos.length) { tbl.innerHTML = '<div class="empty"><div class="empty-icon">💰</div><p>Sem lançamentos</p></div>'; return; }
  tbl.innerHTML = `<table><thead><tr><th>Data</th><th>Tipo</th><th>Descrição</th><th>Pagamento</th><th>Valor</th><th></th></tr></thead>
  <tbody>${d.movimentos.map(m => `<tr class="${m.tipo === 'SAIDA' ? 'row-red' : ''}"><td>${new Date(m.data).toLocaleDateString('pt-BR')}</td><td><span class="badge ${m.tipo === 'ENTRADA' ? 'badge-green' : 'badge-red'}">${m.tipo}</span></td><td>${m.descricao}</td><td>${m.forma_pagamento || '-'}</td><td class="mono fw7">${m.tipo === 'SAIDA' ? '-' : ''}${fmt(m.valor)}</td>
  <td>${m.tipo === 'SAIDA' ? `<button class="btn btn-sm btn-danger" onclick="deletarDespesa(${m.id})">🗑️</button>` : ''}</td></tr>`).join('')}</tbody></table>`;
}

async function novaDespesa() {
  openModal('Nova Despesa (Saída)', `
    <div class="form-grid">
      <div class="form-group full"><label>Descrição *</label><input id="df-desc" placeholder="Ex: Aluguel, Luz, Compra de Peças"></div>
      <div class="form-group"><label>Valor *</label><input id="df-val" value="0,00" oninput="this.value=maskMoney(this.value)"></div>
      <div class="form-group"><label>Data</label><input type="date" id="df-data" value="${today()}"></div>
      <div class="form-group full"><label>Forma de Pagamento</label><select id="df-pgto"><option>DINHEIRO</option><option>PIX</option><option>CARTÃO</option><option>BOLETO</option></select></div>
    </div>
  `, `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-danger" onclick="salvarDespesa()">Confirmar Saída</button>`);
}
async function salvarDespesa() {
  const body = { descricao: document.getElementById('df-desc').value, valor: parseMoney(document.getElementById('df-val').value), data: document.getElementById('df-data').value, forma_pagamento: document.getElementById('df-pgto').value };
  if (!body.descricao || body.valor <= 0) { notify('Preencha descrição e valor', 'error'); return; }
  const r = await api('/api/financeiro/despesas', 'POST', body);
  if (r?.ok) { notify('Despesa lançada'); closeModal(); loadFluxo(); }
}
async function deletarDespesa(id) { if (!confirm('Deseja excluir este lançamento de saída?')) return; const r = await api(`/api/financeiro/despesas/${id}`, 'DELETE'); if (r?.ok) { notify('Lançamento excluído'); loadFluxo(); } }

async function renderReceber() {
  document.getElementById('fin-content').innerHTML = `
    <div class="filters">
      <div class="filter-group"><label>Situação</label><select id="rf-st"><option value="PENDENTE">Abertas / Atrasadas</option><option value="PAGO">Pagas / Recebidas</option><option value="">Todas</option></select></div>
      <div style="display:flex;align-items:flex-end;gap:8px">
        <button class="btn btn-primary" onclick="loadReceber()">🔍 Filtrar</button>
        <button class="btn btn-primary" onclick="novaContaReceber()">+ Nova Conta</button>
      </div>
    </div>
    <div id="receber-resumo" class="stats-grid" style="margin-bottom:20px"></div>
    <div class="card"><div class="card-header">Contas a Receber</div><div class="tbl-wrap" id="receber-tbl"></div></div>`;
  loadReceber();
}

async function loadReceber() {
  const st = document.getElementById('rf-st').value;
  const data = await api(`/api/financeiro/receber?status=${st}`);
  if (!data) return;
  const total = data.reduce((a, b) => a + b.valor_pendente, 0);
  document.getElementById('receber-resumo').innerHTML = `
    <div class="stat-card orange"><div class="stat-label">Total Pendente</div><div class="stat-value">${fmt(total)}</div><div class="stat-sub">${data.length} parcelas</div></div>
  `;
  const tbl = document.getElementById('receber-tbl');
  if (!data.length) { tbl.innerHTML = '<div class="empty"><div class="empty-icon">📅</div><p>Nada a receber</p></div>'; return; }
  tbl.innerHTML = `<table><thead><tr><th>Vencimento</th><th>Cliente</th><th>Descrição</th><th>Valor Parcela</th><th>Restante</th><th>Status</th><th></th></tr></thead>
  <tbody>${data.map(r => {
    const isAtrasada = r.status === 'PENDENTE' && new Date(r.data_vencimento) < new Date(today());
    return `<tr class="${isAtrasada ? 'row-red' : ''}"><td>${new Date(r.data_vencimento).toLocaleDateString('pt-BR')}</td><td class="fw7">${r.cliente_nome || '-'}</td><td>${r.descricao} ${r.num_parcela ? `(${r.num_parcela}/${r.total_parcelas})` : ''}</td><td class="mono">${fmt(r.valor_total)}</td><td class="mono fw7 text-red">${fmt(r.valor_pendente)}</td><td>${badgeStatus(isAtrasada ? 'ATRASADO' : r.status)}</td>
  <td style="display:flex;gap:4px">
    <button class="btn btn-sm btn-primary" onclick="showBaixa(${r.id}, ${r.valor_pendente})">💰 Baixar</button>
    <button class="btn btn-sm" onclick="verHistoricoReceber(${r.id})">📜</button>
    <button class="btn btn-sm btn-danger" onclick="excluirConta(${r.id})">🗑️</button>
  </td></tr>`;
  }).join('')}</tbody></table>`;
}

async function showBaixa(id, valorSugerido) {
  openModal('Baixar Parcela', `
    <div class="form-grid">
      <div class="form-group full"><label>Valor Pagamento *</label><input id="bf-val" value="${fmtN(valorSugerido)}" oninput="this.value=maskMoney(this.value)"></div>
      <div class="form-group"><label>Data Baixa</label><input type="date" id="bf-data" value="${today()}"></div>
      <div class="form-group"><label>Meio</label><select id="bf-pgto"><option>DINHEIRO</option><option>PIX</option><option>CARTÃO</option><option>BOLETO</option></select></div>
    </div>
  `, `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="confirmarBaixa(${id})">Confirmar Baixa</button>`, 'modal-sm');
}
async function confirmarBaixa(id) {
  const body = { valor: parseMoney(document.getElementById('bf-val').value), data: document.getElementById('bf-data').value, forma_pagamento: document.getElementById('bf-pgto').value };
  if (body.valor <= 0) { notify('Valor inválido', 'error'); return; }
  const r = await api(`/api/financeiro/receber/${id}/baixar`, 'POST', body);
  if (r?.ok) { notify('Baixa realizada'); closeModal(); loadReceber(); }
}

async function novaContaReceber() {
  allClientes = await api('/api/clientes') || [];
  const cliOpts = allClientes.map(c => `<option value="${c.id}">${c.nome}</option>`).join('');
  openModal('Nova Conta a Receber', `
    <div class="form-grid">
      <div class="form-group full"><label>Cliente *</label><select id="ncr-cli"><option value="">-- Selecione --</option>${cliOpts}</select></div>
      <div class="form-group full"><label>Descrição *</label><input id="ncr-desc"></div>
      <div class="form-group"><label>Valor Total *</label><input id="ncr-val" value="0,00" oninput="this.value=maskMoney(this.value)"></div>
      <div class="form-group"><label>Data Vencimento</label><input type="date" id="ncr-venc" value="${today()}"></div>
      <div class="form-group full"><label>Parcelar em</label><input type="number" id="ncr-parc" value="1" min="1"></div>
    </div>
  `, `<button class="btn" onclick="closeModal()">Cancelar</button><button class="btn btn-primary" onclick="salvarNovaConta()">Criar Conta</button>`);
}
async function salvarNovaConta() {
  const body = {
    cliente_id: document.getElementById('ncr-cli').value, descricao: document.getElementById('ncr-desc').value,
    valor: parseMoney(document.getElementById('ncr-val').value), data_vencimento: document.getElementById('ncr-venc').value,
    parcelas: parseInt(document.getElementById('ncr-parc').value || 1)
  };
  if (!body.cliente_id || !body.descricao || body.valor <= 0) { notify('Preencha os campos obrigatórios', 'error'); return; }
  const r = await api('/api/financeiro/receber', 'POST', body);
  if (r?.ok) { notify('Conta criada'); closeModal(); loadReceber(); }
}

async function verHistoricoReceber(id) {
  const d = await api(`/api/financeiro/receber/${id}/historico`); if (!d) return;
  const hists = d.map(h => `<tr><td>${new Date(h.data).toLocaleDateString('pt-BR')}</td><td>${h.forma_pagamento}</td><td class="mono fw7">${fmt(h.valor)}</td></tr>`).join('') || '<tr><td colspan="3" style="text-align:center">Sem pagamentos</td></tr>';
  openModal('Histórico de Pagamentos', `
      <div class="tbl-wrap" style="margin-top:10px; border:1px solid var(--border); border-radius:8px;">
        <table>
          <thead><tr><th>Data</th><th>Meio</th><th>Valor</th></tr></thead>
          <tbody>${hists}</tbody>
        </table>
      </div>
      `, `<button class="btn" onclick="closeModal()">Fechar</button>`);
}

async function excluirConta(id) {
  if (!confirm('Deseja excluir permanentemente esta conta e todo o seu histórico de pagamentos?')) return;
  const r = await api('/api/contas_receber/' + id, 'DELETE');
  if (r?.ok) { notify('Conta Excluída com Sucesso'); renderReceber(); }
  else notify('Erro ao excluir', 'error');
}

async function renderRelatorios() {
  document.getElementById('topbar-actions').innerHTML = '';
  document.getElementById('content').innerHTML = `
    <div class="empty">
      <div class="empty-icon">📊</div>
      <p>O módulo de relatórios está sendo preparado e estará disponível em breve.</p>
    </div>`;
}

async function renderSettings() {
  document.getElementById('topbar-actions').innerHTML = '';
  document.getElementById('content').innerHTML = `
    <div class="settings-wrap">
      <div class="settings-tabs">
        <button class="settings-tab active" onclick="switchSettingsTab('geral')">Loja</button>
        <button class="settings-tab" onclick="switchSettingsTab('usuarios')">Usuários</button>
      </div>
      <div id="settings-content" style="margin-top:20px">
        <div class="empty">
          <div class="empty-icon">⚙️</div>
          <p>Selecione uma aba para configurar.</p>
        </div>
      </div>
    </div>`;
}

function switchSettingsTab(tab) {
  document.querySelectorAll('.settings-tab').forEach(b => b.classList.toggle('active', b.textContent.toLowerCase().includes(tab)));
  if (tab === 'usuarios') {
    renderUsuarios();
  } else {
    document.getElementById('settings-content').innerHTML = `
      <div class="empty">
        <div class="empty-icon">🛠️</div>
        <p>Configurações de ${tab} em desenvolvimento.</p>
      </div>`;
  }
}

// ══════════════════════════════════════════════════════════════
// INICIALIZAÇÃO
initAuth();
