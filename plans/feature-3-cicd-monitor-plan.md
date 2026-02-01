# Plan d'implémentation : CICD Monitor

**Issue:** #3 - feat: CICD Monitor - Dashboard de visualisation temps réel
**Branche:** `feature/3-cicd-monitor`
**Date:** 2026-01-29

---

## Vue d'ensemble

Dashboard web temps réel pour visualiser l'exécution du système CICD avec graphe de nodes, timeline, et widgets d'information.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CICD Monitor                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Agents/Workflows .md]                                         │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐ │
│  │ CLI Command  │────▶│   Backend    │────▶│   Frontend Web   │ │
│  │ cicd monitor │     │  WebSocket   │     │   Dashboard      │ │
│  │   --emit     │     │   Server     │     │                  │ │
│  └──────────────┘     └──────────────┘     └──────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phases d'implémentation

### Phase 1 : CLI Event Emitter
**Objectif:** Ajouter commande `cicd monitor` pour émettre des événements

**Fichiers à créer/modifier:**
- `cicd/cli.py` - Ajouter sous-commande `monitor`
- `cicd/monitor.py` - Module de gestion des événements

**Commandes:**
```bash
# Émettre un événement
cicd monitor --emit --agent architect --action start --workflow design-feature

# Démarrer le serveur WebSocket
cicd monitor --serve --port 8765

# Ouvrir le dashboard
cicd monitor --open
```

**Format événement JSON:**
```json
{
  "timestamp": "2026-01-29T10:30:00Z",
  "agent": "architect",
  "action": "start",
  "workflow": "design-feature",
  "parent": null,
  "metadata": {}
}
```

---

### Phase 2 : Backend WebSocket Server
**Objectif:** Serveur qui reçoit les événements et les pousse aux clients web

**Fichiers à créer:**
- `cicd/server.py` - Serveur WebSocket asyncio
- `cicd/events.py` - Gestion des événements et historique

**Fonctionnalités:**
- Recevoir événements via WebSocket ou HTTP POST
- Broadcaster aux clients connectés
- Maintenir historique en mémoire (derniers 1000 événements)
- API REST pour récupérer l'historique

**Endpoints:**
- `WS /ws` - WebSocket pour temps réel
- `POST /api/events` - Recevoir événement
- `GET /api/events` - Historique des événements
- `GET /api/state` - État actuel (agents actifs, workflows en cours)

---

### Phase 3 : Frontend Dashboard
**Objectif:** Interface web avec graphe interactif et timeline

**Fichiers à créer:**
- `cicd/dashboard/` - Dossier pour les assets web
- `cicd/dashboard/index.html` - Page principale
- `cicd/dashboard/app.js` - Application JavaScript
- `cicd/dashboard/styles.css` - Styles

**Composantes UI:**

#### 3.1 Graphe de Nodes
- Utiliser **vis.js** (network) ou **D3.js**
- Nodes = Agents (Architect, Coder, Tester, etc.)
- Edges = Appels entre agents/workflows
- Node actif = surligné en vert
- Animation lors des transitions

#### 3.2 Timeline
- Liste chronologique des événements
- Scroll automatique vers le dernier événement
- Filtre par agent/workflow

#### 3.3 Widgets
- **Agent Actif:** Carte montrant l'agent en cours
- **Workflow:** Nom et progression du workflow actuel
- **Statistiques:** Nombre d'appels, durée, etc.

#### 3.4 Logs
- Zone de texte avec les événements bruts
- Export JSON possible

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│                      CICD Monitor                            │
├────────────────────────┬────────────────────────────────────┤
│                        │  Agent: 🏗️ Architect              │
│                        │  Workflow: design-feature          │
│      GRAPHE            │  Status: ● Active                  │
│      DE NODES          ├────────────────────────────────────┤
│                        │                                    │
│                        │         TIMELINE                   │
│                        │  10:30 architect → start           │
│                        │  10:31 coder → delegated           │
│                        │  10:32 tester → start              │
├────────────────────────┴────────────────────────────────────┤
│                          LOGS                                │
│  {"agent":"architect","action":"start",...}                 │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 4 : Intégration avec les Agents
**Objectif:** Modifier les prompts des agents pour émettre des événements

**Fichiers à modifier:**
- `.cicd/core/agents/*.yaml` - Ajouter instructions d'émission

**Pattern à ajouter dans chaque agent:**
```markdown
## Monitoring (si disponible)

À chaque début d'action, exécuter:
```bash
cicd monitor --emit --agent {agent_name} --action start --workflow {workflow_name}
```

À la fin:
```bash
cicd monitor --emit --agent {agent_name} --action end --workflow {workflow_name}
```
```

---

## Dépendances à ajouter

```toml
# pyproject.toml
[project.optional-dependencies]
monitor = [
    "websockets>=12.0",
    "aiohttp>=3.9",
]
```

---

## Tâches détaillées

### Phase 1 - CLI (Estimé: 4 tâches)
- [x] Créer `cicd/monitor.py` avec classe EventEmitter
- [x] Ajouter sous-commande `monitor` dans `cli.py`
- [x] Implémenter `--emit` pour envoyer événements
- [ ] Ajouter tests unitaires

### Phase 2 - Backend (Estimé: 5 tâches)
- [x] Créer `cicd/server.py` avec serveur WebSocket
- [x] Implémenter `cicd/events.py` pour gestion événements (intégré dans server.py)
- [x] Ajouter endpoint HTTP POST pour événements
- [x] Ajouter endpoint GET pour historique
- [ ] Ajouter tests d'intégration

### Phase 3 - Frontend (Estimé: 6 tâches)
- [x] Créer structure `cicd/dashboard/`
- [x] Implémenter `index.html` avec layout de base
- [x] Intégrer vis.js pour le graphe de nodes
- [x] Implémenter connexion WebSocket en JS
- [x] Créer composants timeline et widgets
- [x] Ajouter styles CSS

### Phase 4 - Intégration (Estimé: 2 tâches)
- [x] Documenter le pattern d'émission pour les agents
- [x] Mettre à jour un agent exemple (architect) avec émission

---

## Critères de succès

1. ✅ `cicd monitor --serve` démarre un serveur WebSocket
2. ✅ `cicd monitor --emit` envoie un événement au serveur
3. ✅ `cicd monitor --open` ouvre le dashboard dans le navigateur
4. ✅ Le graphe affiche les nodes et leurs connexions
5. ✅ Les événements apparaissent en temps réel
6. ✅ La timeline montre l'historique chronologique

---

## Notes techniques

- **Pas de framework lourd:** Vanilla JS + vis.js pour garder simple
- **Serveur léger:** websockets + aiohttp, pas de Django/Flask
- **Données en mémoire:** Pas de base de données, juste mémoire (reset au redémarrage)
- **Port par défaut:** 8765 pour WebSocket, 8080 pour HTTP

---

## Questions ouvertes

1. Faut-il persister les événements sur disque (fichier JSON) ?
2. Faut-il supporter plusieurs sessions simultanées ?
3. Design du graphe : layout automatique ou positions fixes ?

---

*Plan créé par CICD Architect*
