# AI provider gating (config + voice)

Obiettivo
Rendere governabile (enable/disable) laccesso a uno o più motori AI (AI engines) sia via configurazione iniziale sia dinamicamente via comando vocale dagli smart glasses. Il codice di integrazione resta presente anche quando un provider è marcato come NON UTILIZZABILE.

Ambito
Backend: applicazione della policy nella provider selection (routing) e nelle chiamate upstream.
Control-plane: API per aggiornare la policy a runtime (per-tenant), con audit.
UX/Voice: mapping intent vocali  richiesta al backend (auditabile).

Terminologia
Provider: identificativo canonico lowercase (es. openai, claude, huggingface, perplexity).
Policy: insieme di regole che determina quali provider sono attivi per un tenant.

Modello di policy

1) Bootstrap (config iniziale)
- HALO_AI_PROVIDERS_ENABLED (CSV): allowlist opzionale (es. "openai,claude,huggingface"). Se valorizzata, solo questi provider sono candidabili.
- HALO_AI_PROVIDERS_DISABLED (CSV): denylist additiva (es. "perplexity"). Vale anche se ENABLED è valorizzata.
- Regola: se ENABLED è valorizzata  modalità ALLOWLIST; altrimenti  ALLOW_ALL. In entrambi i casi, DISABLED sottrae.

2) Runtime (config dinamica)
- Stato per-tenant: providerPolicy.mode (ALLOW_ALL|ALLOWLIST), providerPolicy.enabled[], providerPolicy.disabled[], providerPolicy.allDisabled (bool), updatedAt, actor (voice|api|config), reason.
- Precedenza: runtime > bootstrap.
- Persistenza: MVP in-memory + export audit (artefatto); post-MVP KV store/DB.

Comandi vocali (smart glasses)
- Halo, disabilita Perplexity  disable(provider=perplexity)
- Halo, abilita Perplexity  enable(provider=perplexity)
- Halo, disabilita tutti i motori  disable(all)
- Halo, abilita tutti i motori  enable(all)
- Halo, quali motori sono attivi?  query(policy)

Semantica operativa (idempotente)
- disable(provider): aggiunge provider a disabled[]
- enable(provider): rimuove provider da disabled[]; se mode=ALLOWLIST aggiunge anche a enabled[]
- disable(all): allDisabled=true (nessun provider candidabile)
- enable(all): allDisabled=false; mode=ALLOW_ALL; enabled=[]; disabled=[]

Comportamento applicativo
- Provider disabilitato: escluso dalla provider selection e da ogni failover automatico.
- Se tutti i provider risultano disabilitati: risposta controllata no provider available con istruzione operativa per riabilitare (voice/config).
- Telemetria/audit: log evento policy-change (tenant, actor, delta, reason) + log decisione routing (provider esclusi per policy).

Requisiti GDPR & Security
- La configurazione bootstrap e ogni change runtime devono transitare su canale cifrato e autenticato, usando lo stesso protocollo di trasmissione già adottato per le comunicazioni devicebackend nel sistema (confidenzialità, integrità, autenticazione).
- Minimizzazione: non persistere audio; persistere solo intent normalizzato (azione, provider, tenant, timestamp, actor, reason).
- Access control: policy-change solo da soggetti autenticati/autorized (tenant-scoped) e tracciati in audit log.

Esempio business
Disdetta abbonamento Perplexity: il provider resta integrato ma viene marcato disabled via HALO_AI_PROVIDERS_DISABLED=perplexity oppure via comando vocale, evitando chiamate e costi.

## Security & GDPR (protected bootstrap config)

Requisito: la configurazione iniziale di gating (allow/deny dei provider) deve essere acquisita e trasmessa in forma cifrata e autenticata, usando lo stesso schema/protocollo di protezione adottato per le comunicazioni tra i device del sistema (es. handshake, session keys, mutual auth).

Vincoli:
- Nessun segreto o token in chiaro su log/telemetria; redaction obbligatoria.
- A riposo (at-rest): storage protetto (OS key store / secret store) e integrità (tamper-evidence).
- Separazione per-tenant: policy isolata e auditabile (actor, timestamp, canale: voice/config/api).
- Least privilege: il gating non deve richiedere esposizione delle API key dei provider al layer voice.

