import re
import os

filepath = r"c:\MinhaLoja\MinhaLoja\templates\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update SIDEBAR nav item
nav_item_html = """
        <div class="nav-sep" id="nav-sep-receber" style="display:none"></div>
        <div class="nav-item" onclick="navigate('receber')" data-page="receber" id="nav-receber" style="display:none">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="5" width="20" height="14" rx="2" />
            <line x1="2" y1="10" x2="22" y2="10" />
            <path d="M7 15h0" />
            <path d="M12 15h0" />
          </svg>
          <span class="nav-label">A Receber</span>
        </div>
"""
if "navigate('receber')" not in html:
    html = html.replace('''<div class="nav-sep" id="nav-sep-admin"''', nav_item_html.lstrip() + '''\n        <div class="nav-sep" id="nav-sep-admin"''')

# 2. Update ALL_MODULE_LABELS
if "receber: 'A Receber'" not in html:
    html = html.replace("financeiro: 'Financeiro',", "financeiro: 'Financeiro', receber: 'A Receber',")

# 3. Update ALL_MODULE_ICONS
if "receber: '💳'" not in html:
    html = html.replace("financeiro: '💰',", "financeiro: '💰', receber: '💳',")

# 4. Update initAuth (permissions check)
check_receber = """
      if (me.papel === 'admin' || me.permissions.includes('financeiro')) {
        document.getElementById('nav-receber').style.display = '';
        document.getElementById('nav-sep-receber').style.display = '';
        if (!me.permissions.includes('receber')) me.permissions.push('receber');
      }
"""
if "document.getElementById('nav-receber')" not in html:
    html = html.replace("if (me.papel === 'admin') {", check_receber + "\n      if (me.papel === 'admin') {")


# 5. Update navigate map
if "receber: renderReceber" not in html:
    html = html.replace("produtos: renderProdutos, clientes: renderClientes, financeiro: renderFinanceiro,", 
                        "produtos: renderProdutos, clientes: renderClientes, financeiro: renderFinanceiro, receber: renderReceber,")

# 6. Add JS functions
js_code = """
    // ══════════════════════════════════════════════════════════════
    // CONTAS A RECEBER
    // ══════════════════════════════════════════════════════════════
    async function renderReceber() {
      document.getElementById('topbar-actions').innerHTML = `
        <button class="topbar-btn primary" onclick="openNovaContaReceber()">+ Nova Conta</button>
      `;
      document.getElementById('content').innerHTML = '<div class="empty"><div class="empty-icon">⏳</div><p>Carregando...</p></div>';
      
      const dash = await api('/api/contas_receber/dashboard');
      const contas = await api('/api/contas_receber');
      if (!dash || !contas) return;

      const statsHtml = `
      <div class="stats-grid">
        <div class="stat-card blue"><div class="stat-icon">💰</div><div class="stat-label">Total a Receber</div><div class="stat-value">${fmt(dash.total_a_receber)}</div></div>
        <div class="stat-card red"><div class="stat-icon">⚠️</div><div class="stat-label">Vencido</div><div class="stat-value text-red">${fmt(dash.vencido)}</div></div>
        <div class="stat-card green"><div class="stat-icon">📈</div><div class="stat-label">Recebido Hoje</div><div class="stat-value text-green">${fmt(dash.recebido_hoje)}</div></div>
        <div class="stat-card purple"><div class="stat-icon">📅</div><div class="stat-label">Recebido no Mês</div><div class="stat-value">${fmt(dash.recebido_mes)}</div></div>
      </div>`;

      let tableHtml = '<div class="card"><div class="tbl-wrap"><table><thead><tr><th>Vencimento</th><th>Cliente</th><th>Descrição</th><th>Valor Total</th><th>Recebido</th><th>Status</th><th>Ações</th></tr></thead><tbody>';
      
      if (contas.length === 0) {
        tableHtml += '<tr><td colspan="7" style="text-align:center;color:var(--text3)">Nenhuma conta a receber encontrada</td></tr>';
      } else {
        contas.forEach(c => {
          let badge = '<span class="badge badge-gray">PENDENTE</span>';
          if (c.status === 'PAGA') badge = '<span class="badge badge-green">PAGA</span>';
          else if (c.status === 'PARCIAL') badge = '<span class="badge badge-blue">PARCIAL</span>';
          
          if (c.atrasada) badge += ' <span class="badge badge-red" style="margin-left:5px">ATRASADA</span>';

          const dtVenc = c.data_vencimento.split('-').reverse().join('/');
          
          tableHtml += `
          <tr>
            <td class="mono">${dtVenc}</td>
            <td class="fw7">${c.cliente_nome || 'Desconhecido'}</td>
            <td>${c.descricao}</td>
            <td class="mono fw7">${fmt(c.valor_total)}</td>
            <td class="mono text-green">${fmt(c.total_recebido)}</td>
            <td>${badge}</td>
            <td>
              <div style="display:flex;gap:5px;align-items:center;">
                <button class="btn btn-sm btn-success" style="padding:4px 8px;font-size:11px" onclick="openReceberPagamento(${c.id})" title="Registrar Pagamento">💰 Receber</button>
                <button class="btn btn-sm" style="padding:4px 8px;font-size:11px" onclick="verDetalhesConta(${c.id})" title="Detalhes/Histórico">👁️</button>
                <button class="icon-btn danger" style="width:24px;height:24px" onclick="excluirConta(${c.id})" title="Excluir">🗑️</button>
              </div>
            </td>
          </tr>`;
        });
      }
      tableHtml += '</tbody></table></div></div>';

      document.getElementById('content').innerHTML = statsHtml + tableHtml;
    }

    async function openNovaContaReceber() {
      allClientes = await api('/api/clientes') || [];
      const cliOptions = allClientes.map(c => `<option value="${c.id}">${c.nome} - ${c.cpf_cnpj || ''}</option>`).join('');
      
      openModal('Nova Conta a Receber', `
      <div class="form-grid">
        <div class="form-group full">
          <label>Cliente (Selecione ou deixe em branco para novo)</label>
          <select id="nova-conta-cli"><option value="">-- Selecione --</option>${cliOptions}</select>
        </div>
        <div class="form-group full">
          <label>Novo Cliente (Nome Rápido)</label>
          <input type="text" id="nova-conta-novo-cli" placeholder="Ex: Higor">
        </div>
        <div class="form-group full">
          <label>Descrição (Referência da dívida)</label>
          <input type="text" id="nova-conta-desc" placeholder="Ex: Fiado João, Máquina Conserto">
        </div>
        <div class="form-group">
          <label>Valor Total (R$)</label>
          <input type="text" id="nova-conta-valor" placeholder="0,00" oninput="this.value=maskMoney(this.value)">
        </div>
        <div class="form-group">
          <label>Data de Vencimento</label>
          <input type="date" id="nova-conta-venc" value="${today()}">
        </div>
      </div>
      `, `<button class="btn" onclick="closeModal()">Cancelar</button>
         <button class="btn btn-primary" onclick="salvarNovaContaReceber()">Salvar</button>`);
    }

    async function salvarNovaContaReceber() {
      const cid = document.getElementById('nova-conta-cli').value;
      const novoNome = document.getElementById('nova-conta-novo-cli').value.trim();
      if (!cid && !novoNome) { notify('Selecione um cliente ou informe um novo nome', 'error'); return; }
      
      const val = parseMoney(document.getElementById('nova-conta-valor').value);
      if (val <= 0) { notify('Valor deve ser maior que zero', 'error'); return; }
      const desc = document.getElementById('nova-conta-desc').value.trim();
      if (!desc) { notify('A descrição é obrigatória', 'error'); return; }
      
      const payload = {
        descricao: desc,
        valor_total: val,
        data_vencimento: document.getElementById('nova-conta-venc').value,
      };
      if (cid) {
        payload.cliente_id = parseInt(cid);
      } else {
        payload.novo_cliente = { nome: novoNome };
      }
      
      const r = await api('/api/contas_receber', 'POST', payload);
      if (r?.ok) {
        notify('Conta registrada com sucesso!');
        closeModal();
        renderReceber();
      } else {
        notify(r?.error || 'Erro ao registrar conta', 'error');
      }
    }

    async function openReceberPagamento(id) {
      const data = await api('/api/contas_receber/' + id);
      if (!data) return;
      const c = data.conta;
      const faltante = c.valor_total - c.total_recebido;
      if (faltante <= 0) { notify('Esta conta já está totalmente paga.', 'info'); return; }
      
      openModal('Registrar Pagamento', `
      <div style="margin-bottom:15px; background:var(--bg3); padding:10px; border-radius:8px">
        <strong>${c.cliente_nome || 'Desconhecido'}</strong><br/>
        <span class="text-muted">${c.descricao}</span><br/>
        <span class="fw7">Total: ${fmt(c.valor_total)} | Faltante: <span class="text-red">${fmt(Math.max(0, faltante))}</span></span>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label>Valor a Pagar (R$)</label>
          <input type="text" id="pagamento-valor" value="${maskMoney(faltante.toString())}" oninput="this.value=maskMoney(this.value)">
        </div>
        <div class="form-group">
          <label>Data</label>
          <input type="date" id="pagamento-data" value="${today()}">
        </div>
        <div class="form-group full">
          <label>Forma de Pagamento</label>
          <select id="pagamento-forma">
            <option value="DINHEIRO">Dinheiro</option>
            <option value="PIX">PIX</option>
            <option value="CARTAO">Cartão</option>
            <option value="BOLETO">Boleto/Transferência</option>
          </select>
        </div>
      </div>
      `, `<button class="btn" onclick="closeModal()">Cancelar</button>
         <button class="btn btn-success" onclick="salvarPagamentoConta(${id})">Confirmar Pagamento</button>`);
    }

    async function salvarPagamentoConta(id) {
      const val = parseMoney(document.getElementById('pagamento-valor').value);
      if (val <= 0) { notify('Valor inválido', 'error'); return; }
      
      const payload = {
        valor_pago: val,
        data_pagamento: document.getElementById('pagamento-data').value,
        forma_pagamento: document.getElementById('pagamento-forma').value
      };
      
      const r = await api('/api/contas_receber/' + id + '/recebimento', 'POST', payload);
      if (r?.ok) {
        notify('Pagamento registrado. Status atualizado: ' + r.novo_status);
        closeModal();
        renderReceber();
      } else notify(r?.error || 'Erro', 'error');
    }

    async function verDetalhesConta(id) {
      const data = await api('/api/contas_receber/' + id);
      if (!data) return;
      const c = data.conta;
      const recs = data.recebimentos;
      
      let hists = recs.length ? recs.map(r => `
        <tr>
          <td>${r.data_pagamento.split('-').reverse().join('/')}</td>
          <td><span class="badge badge-gray">${r.forma_pagamento}</span></td>
          <td class="text-green fw7">+ ${fmt(r.valor_pago)}</td>
        </tr>
      `).join('') : '<tr><td colspan="3" class="text-muted" style="text-align:center">Nenhum pagamento registrado</td></tr>';
      
      openModal('Detalhes da Conta', `
      <div style="background:var(--bg3); padding:15px; border-radius:8px; margin-bottom:15px; display:flex; flex-direction:column; gap:8px">
        <h4 style="margin-bottom:4px">${c.cliente_nome || 'Desconhecido'}</h4>
        <div class="text-muted" style="font-size:12px">${c.descricao}</div>
        <div class="divider" style="margin:8px 0"></div>
        <div style="display:flex; justify-content:space-between">
            <span><strong>Valor Total:</strong> ${fmt(c.valor_total)}</span>
            <span><strong>Recebido:</strong> <span class="text-green">${fmt(c.total_recebido)}</span></span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:5px">
            <span><strong>Vencimento:</strong> ${c.data_vencimento.split('-').reverse().join('/')}</span>
            <span><strong>Status:</strong> ${c.status}</span>
        </div>
      </div>
      
      <div class="section-title">Histórico de Pagamentos</div>
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

    // ══════════════════════════════════════════════════════════════
    // SETTINGS / COMPLETED
"""

if "async function renderReceber" not in html:
    html = html.replace("</script>", js_code + "\n  </script>")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(html)
print("PATCH SUCCESSFUL!")
