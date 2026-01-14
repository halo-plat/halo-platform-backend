# AI provider gating (config + voice)

Obiettivo
Rendere governabile (enable/disable) laccesso a uno o più motori AI (AI engines) sia via configurazione iniziale sia dinamicamente via comando vocale dagli smart glasses. Il codice di integrazione resta presente anche quando un provider è marcato NON UTILIZZABILE.

Scope
- Backend: applicazione policy di abilitazione/disabilitazione nella selezione provider e nelle chiamate upstream.
- Control-plane: endpoint/command bus per aggiornare la policy a runtime (per-tenant).
- UX/Voice: mapping comandi vocali  intent  richiesta al backend (auditabile).

Modello di policy
1) Config statica (bootstrap)
- Env var: HALO_AI_PROVIDERS_ENABLED (CSV) es. "openai,claude,huggingface" (assenza = default allow-all).
- Env var: HALO_AI_PROVIDERS_DISABLED (CSV) es. "perplexity" (override di deny).
- Regola: se ENABLED è valorizzata, è allowlist; DISABLED è denylist additiva.

2) Config dinamica (runtime)
- Stato per-tenant: providerPolicy.enabled[] / providerPolicy.disabled[] + timestamp + actor (voice/config/api).
- Precedenza: runtime > bootstrap. Persistenza: (MVP) in-memory + export su artifact di audit; (post-MVP) KV store.

Comandi vocali (smart glasses)
- Halo, disabilita Perplexity  disable(provider=perplexity)
- Halo, abilita Perplexity  enable(provider=perplexity)
- Halo, disabilita tutti i motori  disable(all)
- Halo, abilita tutti i motori  enable(all)
- Halo, quali motori sono attivi?  query(policy)
Nota: i nomi provider sono normalizzati (lowercase, canonical id).

Comportamento applicativo
- Provider disabilitato: escluso dalla provider selection (routing) e da ogni failover automatico.
- Se tutti i provider risultano disabilitati: risposta controllata con errore no provider available + istruzione operativa per riabilitare (voice/config).
- Telemetria/audit: log evento policy-change (tenant, actor, delta, reason) + log di decisione di routing (provider esclusi per policy).

Esempio business
Scenario: disdetta abbonamento Perplexity  provider perplexity resta integrato ma viene marcato disabled via HALO_AI_PROVIDERS_DISABLED=perplexity oppure via comando vocale, evitando chiamate e costi.

