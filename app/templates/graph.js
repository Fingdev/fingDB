const API_CONFIG = {
  apiUrl: (function() {
    const origin = window.location.origin;
    const path = window.location.pathname;
    const lastSlash = path.lastIndexOf('/');
    const basePath = lastSlash > 0 ? path.substring(0, lastSlash) : path;
    console.log('API_URL:', origin + (basePath || '/'), 'path:', path);
    return origin + (basePath || '/');
  })(),
  getToken: function() {
    return localStorage.getItem('access_token') || '';
  }
};
   const { createApp, ref, computed, onMounted, watch } = Vue;

    const PERIODO_COLORS = {
      'bisemestral': '#58a6ff',
      'par': '#bc8cff',
      'impar': '#f778ba'
    };

    function getPeriodoColor(periodo) {
      if (!periodo) return '#58a6ff';
      const p = String(periodo).toLowerCase().trim();
      return PERIODO_COLORS[p] || '#58a6ff';
    }

    function capitalize(str) {
      if (!str) return '';
      return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    }

    function getInstitutoName(instituto_id) {
      const nameMap = {
        1: 'Instituto de Computación',
        2: 'Instituto de Matemática y Estadística',
        3: 'Instituto de Ingeniería Eléctrica',
        4: 'Instituto de Agrimensura',
        5: 'Instituto de Mecánica de los Fluidos',
        6: 'Instituto de Física',
        7: 'Instituto de Ingeniería Mecánica',
        8: 'Instituto de Ensayo de Materiales',
        9: 'Instituto de Estructuras y Transporte',
        10: 'Instituto de Ingeniería Química',
        11: 'Departamento de Inserción Social'
      };
      return nameMap[instituto_id] || ('Instituto #' + instituto_id);
    }

    function getAuthHeaders() {
      return {
        'Authorization': 'Bearer ' + API_CONFIG.getToken()
      };
    }

    createApp({
      setup() {
        const apiUrl = ref(API_CONFIG.apiUrl);
        const materias = ref([]);
        const loading = ref(false);
        const error = ref(null);
        const searchQuery = ref('');
        const highlightedId = ref(null);
        const selectedMateria = ref(null);
        const filtro = ref('todos');
        const sidebarCollapsed = ref(false);
        const isMobile = ref(false);
        
        const selectedCareer = ref(null);
        const selectedProfile = ref(null);
        const mathInitEnabled = ref(true);
        const carreras = ref([]);
        const perfiles = ref([]);
        
        const isLoggedIn = ref(false);
        const showLoginModal = ref(false);
        const loginUsername = ref('');
        const loginPassword = ref('');
        const loginError = ref('');
        const loginLoading = ref(false);
        
        function removeAccents(str) {
          if (!str) return '';
          return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        }
        
        let svg = null;
        let g = null;
        let zoom = null;
        let nodeMap = new Map();
        let containerBounds = null;
        let currentTransform = d3.zoomIdentity;

        const filteredMaterias = computed(() => {
          let result = materias.value;
          
          if (selectedCareer.value) {
            const obligatoriasIds = new Set((selectedCareer.value.materias_obligatorias || []).map(m => Number(m.id)));
            const opcionalesIds = new Set((selectedCareer.value.materias_opcionales || []).map(m => Number(m.id)));
            let careerMateriaIds = new Set([...obligatoriasIds, ...opcionalesIds]);
            
            if (selectedProfile.value) {
              const profileObligatorias = selectedProfile.value.materias_obligatorias || [];
              profileObligatorias.forEach(m => careerMateriaIds.add(Number(m.id)));
            }
            
            result = result.filter(m => careerMateriaIds.has(Number(m.id)));
          }
          
          if (searchQuery.value) {
            const q = removeAccents(searchQuery.value.toLowerCase());
            result = result.filter(m => removeAccents(m.name.toLowerCase()).includes(q));
          }
          
          return result;
        });

        function setFiltro(val) {
          filtro.value = val;
        }

        async function loadCarreras() {
          try {
            const response = await fetch(`${apiUrl.value}/carreras`, {
              headers: getAuthHeaders()
            });
            if (response.ok) {
              carreras.value = await response.json();
              setTimeout(function() { renderGraph(); }, 100);
            }
          } catch (e) {
            console.error('Error loading carreras:', e);
          }
        }
        
        async function loadPerfiles(carreraId) {
          try {
            const response = await fetch(`${apiUrl.value}/perfiles/by-carrera/${carreraId}`, {
              headers: getAuthHeaders()
            });
            if (response.ok) {
              perfiles.value = await response.json();
            }
          } catch (e) {
            console.error('Error loading perfiles:', e);
          }
        }

        function onCareerChange() {
          const oldCareer = selectedCareer.value ? selectedCareer.value.name : null;
          selectedProfile.value = null;
          if (selectedCareer.value) {
            sendEvent('career_select', {
              career_id: selectedCareer.value.id,
              career_name: selectedCareer.value.name,
              previous_career: oldCareer
            });
            loadPerfiles(selectedCareer.value.id).then(function() {
              renderGraph();
            });
          } else {
            perfiles.value = [];
            sendEvent('career_deselect', { previous_career: oldCareer });
            renderGraph();
          }
        }
        
        function onProfileChange() {
          if (selectedProfile.value) {
            sendEvent('profile_select', {
              profile_id: selectedProfile.value.id,
              profile_name: selectedProfile.value.name,
              career_id: selectedCareer.value ? selectedCareer.value.id : null
            });
          }
          setTimeout(function() { renderGraph(); }, 100);
        }
        
        function onMathInitChange() {
          sendEvent('math_init_toggle', {
            enabled: mathInitEnabled.value
          });
          setTimeout(function() { renderGraph(); }, 100);
        }

        function getMateriaStatus(materiaId) {
          if (!selectedCareer.value) {
            return null;
          }
          
          const oid = Number(materiaId);
          const obligatorias = selectedCareer.value.materias_obligatorias || [];
          const opcionales = selectedCareer.value.materias_opcionales || [];
          
          if (selectedProfile.value) {
            const perfilObligatorias = selectedProfile.value.materias_obligatorias || [];
            for (const pm of perfilObligatorias) {
              if (Number(pm.id) === oid) {
                return 'perfil_obligatoria';
              }
            }
          }
          
          for (const m of obligatorias) {
            if (Number(m.id) === oid) {
              return 'obligatoria';
            }
          }
          
          for (const m of opcionales) {
            if (Number(m.id) === oid) {
              return 'opcional';
            }
          }
          
          return 'excluded';
        }

        const institutos = ref([]);
        
        async function loadData() {
          loading.value = true;
          error.value = null;
          
          try {
            const instResponse = await fetch(`${apiUrl.value}/institutos`, {
              headers: getAuthHeaders()
            });
            if (instResponse.ok) {
              institutos.value = await instResponse.json();
            }
            
            const response = await fetch(`${apiUrl.value}/materias/all/con-previas`, {
              headers: getAuthHeaders()
            });
            
            if (!response.ok) {
              throw new Error(`Error ${response.status}`);
            }
            
            materias.value = await response.json();
          } catch (e) {
            error.value = e.message;
            console.error('Load error:', e);
          } finally {
            loading.value = false;
          }
        }

        function buildGraphData() {
          let materiasList = [...materias.value];
          
          const mathInitMateria = materiasList.find(m => 
            removeAccents(m.name.toLowerCase()).includes('matematica inicial')
          );
          
          if (!mathInitEnabled.value && mathInitMateria) {
            const mathInitId = mathInitMateria.id;
            materiasList = materiasList.filter(m => m.id !== mathInitId);
            
            materiasList = materiasList.map(m => {
              const previasAprobado = (m.previas_aprobado || []).filter(p => p.id !== mathInitId);
              const previasExonerado = (m.previas_exonerado || []).filter(p => p.id !== mathInitId);
              return {
                ...m,
                previas_aprobado: previasAprobado,
                previas_exonerado: previasExonerado
              };
            });
          }
          
          if (selectedCareer.value) {
            const obligatoriasIds = new Set((selectedCareer.value.materias_obligatorias || []).map(m => Number(m.id)));
            const opcionalesIds = new Set((selectedCareer.value.materias_opcionales || []).map(m => Number(m.id)));
            let careerMateriaIds = new Set([...obligatoriasIds, ...opcionalesIds]);
            
            if (selectedProfile.value) {
              const profileObligatorias = selectedProfile.value.materias_obligatorias || [];
              profileObligatorias.forEach(m => careerMateriaIds.add(Number(m.id)));
            }
            
            materiasList = materiasList.filter(m => careerMateriaIds.has(Number(m.id)));
          }
          
          const nodes = materiasList.map(m => {
            console.log('Mapping materia:', m.name, 'codigo:', m.codigo);
            return {
              id: m.id,
              name: m.name,
              codigo: m.codigo || null,
              periodo: m.periodo,
              creditos: m.creditos || 0,
              instituto_id: m.instituto_id,
              hasPrevia: ((m.previas_aprobado?.length || 0) > 0) || ((m.previas_exonerado?.length || 0) > 0)
            };
          });
          
          const links = [];
          
          materiasList.forEach(materia => {
            const allPrevias = [
              ...(materia.previas_aprobado || []),
              ...(materia.previas_exonerado || [])
            ];
            allPrevias.forEach(prev => {
              const prevExists = materiasList.some(m => m.id === prev.id);
              if (prevExists) {
                links.push({ source: prev.id, target: materia.id });
              }
            });
          });
          
          return { nodes, links };
        }

        function calculateLevels(nodes, links) {
          const levels = new Map();
          
          function getLevel(nodeId, visited = new Set()) {
            if (visited.has(nodeId)) return 0;
            visited.add(nodeId);
            
            const incomingLinks = links.filter(l => {
              const targetId = typeof l.target === 'object' ? l.target.id : l.target;
              return targetId === nodeId;
            });
            
            if (incomingLinks.length === 0) {
              levels.set(nodeId, 0);
              return 0;
            }
            
            let maxPrevLevel = 0;
            incomingLinks.forEach(l => {
              const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
              maxPrevLevel = Math.max(maxPrevLevel, getLevel(sourceId, new Set(visited)));
            });
            
            const finalLevel = maxPrevLevel + 1;
            levels.set(nodeId, finalLevel);
            return finalLevel;
          }
          
          nodes.forEach(n => {
            if (!levels.has(n.id)) {
              getLevel(n.id);
            }
          });
          
          return levels;
        }

        function renderGraph() {
          const savedTransform = currentTransform;
          
          const container = document.getElementById('graph');
          container.innerHTML = '';
          
          svg = null;
          g = null;
          zoom = null;
          nodeMap.clear();
          
          containerBounds = container.getBoundingClientRect();
          const width = containerBounds.width;
          const height = containerBounds.height;
          
          svg = d3.select('#graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height);
          
          const defs = svg.append('defs');
          
          defs.append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '-0 -4 8 8')
            .attr('refX', 8)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 5)
            .attr('markerHeight', 5)
            .append('path')
            .attr('d', 'M 0,-3 L 6,0 L 0,3')
            .attr('fill', '#30363d');

          g = svg.append('g').attr('class', 'smooth-transition');
          
          zoom = d3.zoom()
            .scaleExtent([0.3, 2])
            .on('zoom', (event) => {
              g.classed('smooth-transition', false);
              currentTransform = event.transform;
              g.attr('transform', event.transform);
            })
            .on('end', () => {
              g.classed('smooth-transition', true);
            });
          
          svg.call(zoom).on('dblclick.zoom', null);
          
          if (savedTransform && savedTransform !== d3.zoomIdentity) {
            g.classed('smooth-transition', true);
            svg.call(zoom.transform, savedTransform);
            currentTransform = savedTransform;
          } else {
            g.classed('smooth-transition', true);
          }
          
          const { nodes, links } = buildGraphData();
          
          if (nodes.length === 0) {
            return;
          }

          const levels = calculateLevels(nodes, links);
          
          const nodesByInstituto = {};
          nodes.forEach(n => {
            const instId = n.instituto_id || 0;
            if (!nodesByInstituto[instId]) {
              nodesByInstituto[instId] = [];
            }
            nodesByInstituto[instId].push(n);
          });
          
          const instituteIds = Object.keys(nodesByInstituto).sort((a, b) => a - b);
          
          const MAX_NODES_PER_LEVEL = 4;
          const visualLevels = [];
          const nodeVisualLevels = {};
          
          instituteIds.forEach(instId => {
            const instNodes = nodesByInstituto[instId];
            
            const levelGroups = {};
            instNodes.forEach(n => {
              const origLevel = levels.get(n.id) || 0;
              if (!levelGroups[origLevel]) {
                levelGroups[origLevel] = [];
              }
              levelGroups[origLevel].push(n);
            });
            
            let instNextLevel = {};
            Object.keys(levelGroups).forEach(origLevel => {
              const groupNodes = levelGroups[origLevel];
              
              groupNodes.forEach((node, idx) => {
                let baseLevel = parseInt(origLevel);
                if (!instNextLevel[instId]) instNextLevel[instId] = {};
                
                if (instNextLevel[instId][baseLevel] === undefined) {
                  instNextLevel[instId][baseLevel] = baseLevel;
                }
                
                let visualLevel = instNextLevel[instId][baseLevel];
                if (idx >= MAX_NODES_PER_LEVEL) {
                  const overflowLevels = Math.floor(idx / MAX_NODES_PER_LEVEL);
                  visualLevel = baseLevel + overflowLevels;
                }
                
                if (idx === MAX_NODES_PER_LEVEL - 1 || (idx > MAX_NODES_PER_LEVEL && (idx + 1) % MAX_NODES_PER_LEVEL === 0)) {
                  const nextOverflow = Math.floor((idx + 1) / MAX_NODES_PER_LEVEL);
                  instNextLevel[instId][baseLevel] = baseLevel + nextOverflow;
                }
                
                nodeVisualLevels[node.id] = visualLevel;
                
                while (visualLevels.length <= visualLevel) {
                  visualLevels.push([]);
                }
                visualLevels[visualLevel].push({ node, instId });
              });
            });
          });
          
          let hasConflicts = true;
          while (hasConflicts) {
            hasConflicts = false;
            
            links.forEach(link => {
              const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
              const targetId = typeof link.target === 'object' ? link.target.id : link.target;
              
              const sourceLevel = nodeVisualLevels[sourceId];
              const targetLevel = nodeVisualLevels[targetId];
              
              if (targetLevel <= sourceLevel) {
                nodeVisualLevels[targetId] = sourceLevel + 1;
                hasConflicts = true;
              }
            });
          }
          
          const finalVisualLevels = [];
          Object.keys(nodeVisualLevels).forEach(nodeId => {
            const vl = nodeVisualLevels[nodeId];
            const node = nodes.find(n => n.id === Number(nodeId));
            const instId = node ? (node.instituto_id || 0) : 0;
            while (finalVisualLevels.length <= vl) {
              finalVisualLevels.push([]);
            }
            finalVisualLevels[vl].push({ node, instId: String(instId) });
          });

          const nodeWidth = 200;
          const nodeHeight = 64;
          const horizontalGap = 30;
          const verticalGap = 80;
          const marginX = 100;
          const marginY = 60;
          const instituteGap = 80;
          
          const instituteMaxWidth = {};
          instituteIds.forEach(instId => {
            let maxCount = 0;
            for (let vLevel = 0; vLevel < finalVisualLevels.length; vLevel++) {
              const count = finalVisualLevels[vLevel].filter(item => item.instId == instId).length;
              if (count > maxCount) maxCount = count;
            }
            instituteMaxWidth[instId] = maxCount * nodeWidth + Math.max(0, maxCount - 1) * horizontalGap;
          });
          
          const instituteStartX = {};
          let currentX = marginX;
          instituteIds.forEach(instId => {
            instituteStartX[instId] = currentX;
            currentX += instituteMaxWidth[instId] + instituteGap;
          });
          
          const totalWidth = currentX - marginX;
          const viewportCenter = width / 2;
          const globalOffsetX = viewportCenter - totalWidth / 2;
          
          for (let vLevel = 0; vLevel < finalVisualLevels.length; vLevel++) {
            const levelItems = finalVisualLevels[vLevel];
            if (levelItems.length === 0) continue;
            
            const y = marginY + vLevel * (nodeHeight + verticalGap);
            
            const byInstitute = {};
            levelItems.forEach(item => {
              const instId = item.instId;
              if (!byInstitute[instId]) byInstitute[instId] = [];
              byInstitute[instId].push(item.node);
            });
            
            instituteIds.forEach(instId => {
              const nodesAtThisLevel = byInstitute[instId] || [];
              if (nodesAtThisLevel.length === 0) return;
              
              const instStart = instituteStartX[instId] + globalOffsetX - marginX;
              const instWidth = instituteMaxWidth[instId];
              const groupWidth = nodesAtThisLevel.length * nodeWidth + Math.max(0, nodesAtThisLevel.length - 1) * horizontalGap;
              const startX = instStart + (instWidth - groupWidth) / 2;
              
              nodesAtThisLevel.forEach((node, i) => {
                node.x = startX + i * (nodeWidth + horizontalGap) + nodeWidth / 2;
                node.y = y + nodeHeight / 2;
              });
            });
          }

          nodeMap.clear();

          links.forEach(linkData => {
            const sourceNode = nodes.find(n => n.id === (typeof linkData.source === 'object' ? linkData.source.id : linkData.source));
            const targetNode = nodes.find(n => n.id === (typeof linkData.target === 'object' ? linkData.target.id : linkData.target));
            
            if (!sourceNode || !targetNode) return;
            
            const x1 = sourceNode.x;
            const y1 = sourceNode.y + nodeHeight / 2 + 2;
            const x2 = targetNode.x;
            const y2 = targetNode.y - nodeHeight / 2 - 2;
            
            const midY = (y1 + y2) / 2;
            
            const path = d3.path();
            path.moveTo(x1, y1);
            path.bezierCurveTo(x1, midY, x2, midY, x2, y2);
            
            g.append('path')
              .attr('class', 'link')
              .attr('data-source', linkData.source)
              .attr('data-target', linkData.target)
              .attr('d', path.toString())
              .style('pointer-events', 'none')
              .style('fill', 'none')
              .style('stroke', '#8b949e')
              .style('stroke-width', '1.5px')
              .style('opacity', '0.7');
          });
          
          const node = g.selectAll('.node-card')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', 'node-card')
            .attr('transform', d => `translate(${d.x - nodeWidth/2}, ${d.y - nodeHeight/2})`)
            .style('cursor', 'pointer');

          node.append('rect')
            .attr('width', nodeWidth)
            .attr('height', nodeHeight)
            .attr('rx', 6)
            .style('fill', '#21262d')
            .style('stroke', function(d) {
              const status = getMateriaStatus(d.id);
              if (status === 'obligatoria') return '#ffffff';
              if (status === 'perfil_obligatoria') return '#f0883e';
              if (status === 'opcional') return '#d4a72c';
              return '#30363d';
            })
            .style('stroke-width', function(d) {
              const status = getMateriaStatus(d.id);
              return (status === 'obligatoria' || status === 'perfil_obligatoria' || status === 'opcional') ? '3px' : '1px';
            })
            .style('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
              highlightLinks(d.id);
            })
            .on('mouseleave', function(event, d) {
              clearHighlight();
            })
            .on('click', function(event, d) {
              event.stopPropagation();
              const materia = materias.value.find(m => m.id === d.id);
              selectedMateria.value = materia;
              if (materia) {
                sendEvent('materia_click', {
                  materia_id: materia.id,
                  materia_name: materia.name,
                  materia_codigo: materia.codigo || null,
                  materia_periodo: materia.periodo,
                  materia_creditos: materia.creditos,
                  instituto_id: materia.instituto_id
                });
              }
            });

          node.append('circle')
            .attr('cx', 10)
            .attr('cy', nodeHeight / 2)
            .attr('r', 5)
            .attr('fill', d => getPeriodoColor(d.periodo));

          const lineHeight = 12;
          const startY = 18;
          const maxLines = 2;
          
          node.each(function(d) {
            const words = d.name.split(' ');
            let lines = [];
            let currentLine = '';
            
            words.forEach(word => {
              const testLine = currentLine ? currentLine + ' ' + word : word;
              if (testLine.length <= 30) {
                currentLine = testLine;
              } else {
                if (currentLine) lines.push(currentLine);
                currentLine = word;
              }
            });
            if (currentLine) lines.push(currentLine);
            if (lines.length > maxLines) {
              lines = lines.slice(0, maxLines);
              lines[maxLines - 1] = lines[maxLines - 1].slice(0, 27) + '...';
            }
            
            const group = d3.select(this);
            
            lines.forEach((line, i) => {
              group.append('text')
                .attr('x', nodeWidth / 2)
                .attr('y', startY + i * lineHeight)
                .attr('text-anchor', 'middle')
                .text(line);
            });
            
            if (d.codigo) {
              console.log('Rendering codigo:', d.codigo, 'for materia:', d.name);
              group.append('text')
                .attr('class', 'codigo')
                .attr('x', nodeWidth / 2)
                .attr('y', nodeHeight - 22)
                .attr('text-anchor', 'middle')
                .attr('font-size', '10px')
                .attr('fill', '#8b949e')
                .text(d.codigo);
            }
            
            group.append('text')
              .attr('class', 'creditos')
              .attr('x', nodeWidth / 2)
              .attr('y', nodeHeight - 10)
              .attr('text-anchor', 'middle')
              .text(`${d.creditos} créd.`);
          });
        }

        function focusAndOpenModal(id, openModal = true) {
          try {
            if (!g) return;
            
            const materia = materias.value.find(m => m.id === id);
            if (materia) {
              sendEvent('materia_focus', {
                materia_id: materia.id,
                materia_name: materia.name,
                materia_codigo: materia.codigo || null,
                open_modal: openModal
              });
            }
            
            if (isMobile.value) {
              sidebarCollapsed.value = true;
            }
            
            const container = document.getElementById('graph');
            const bounds = container.getBoundingClientRect();
            const width = bounds.width;
            const height = bounds.height;
            
            let materiasList = [...materias.value];
            
            const mathInitMateria = materiasList.find(m => 
              removeAccents(m.name.toLowerCase()).includes('matematica inicial')
            );
            if (!mathInitEnabled.value && mathInitMateria) {
              materiasList = materiasList.filter(m => m.id !== mathInitMateria.id);
            }
            
            if (selectedCareer.value) {
              const obligatoriasIds = new Set((selectedCareer.value.materias_obligatorias || []).map(m => Number(m.id)));
              const opcionalesIds = new Set((selectedCareer.value.materias_opcionales || []).map(m => Number(m.id)));
              let careerMateriaIds = new Set([...obligatoriasIds, ...opcionalesIds]);
              
              if (selectedProfile.value) {
                const profileObligatorias = selectedProfile.value.materias_obligatorias || [];
                profileObligatorias.forEach(m => careerMateriaIds.add(Number(m.id)));
              }
              
              materiasList = materiasList.filter(m => careerMateriaIds.has(Number(m.id)));
            }
            
            const nodesAll = materiasList.map(m => ({
              id: m.id,
              name: m.name,
              codigo: m.codigo || null,
              periodo: m.periodo,
              creditos: m.creditos || 0,
              instituto_id: m.instituto_id,
              hasPrevia: ((m.previas_aprobado?.length || 0) > 0) || ((m.previas_exonerado?.length || 0) > 0)
            }));
            
            const linksAll = [];
            materiasList.forEach(materia => {
              const allPrevias = [
                ...(materia.previas_aprobado || []),
                ...(materia.previas_exonerado || [])
              ];
              allPrevias.forEach(prev => {
                if (materiasList.some(m => m.id === prev.id)) {
                  linksAll.push({ source: prev.id, target: materia.id });
                }
              });
            });
            
            const levelsAll = calculateLevels(nodesAll, linksAll);
            
            const nodesByInstituto = {};
            nodesAll.forEach(n => {
              const instId = n.instituto_id || 0;
              if (!nodesByInstituto[instId]) {
                nodesByInstituto[instId] = [];
              }
              nodesByInstituto[instId].push(n);
            });
            
            const instituteIds = Object.keys(nodesByInstituto).sort((a, b) => a - b);
            
            const MAX_NODES_PER_LEVEL = 4;
            const visualLevelsAll = [];
            const nodeVisualLevelsAll = {};
            
            instituteIds.forEach(instId => {
              const instNodes = nodesByInstituto[instId];
              
              const levelGroups = {};
              instNodes.forEach(n => {
                const origLevel = levelsAll.get(n.id) || 0;
                if (!levelGroups[origLevel]) {
                  levelGroups[origLevel] = [];
                }
                levelGroups[origLevel].push(n);
              });
              
              let instNextLevel = {};
              Object.keys(levelGroups).forEach(origLevel => {
                const groupNodes = levelGroups[origLevel];
                
                groupNodes.forEach((node, idx) => {
                  let baseLevel = parseInt(origLevel);
                  if (!instNextLevel[instId]) instNextLevel[instId] = {};
                  
                  if (instNextLevel[instId][baseLevel] === undefined) {
                    instNextLevel[instId][baseLevel] = baseLevel;
                  }
                  
                  let visualLevel = instNextLevel[instId][baseLevel];
                  if (idx >= MAX_NODES_PER_LEVEL) {
                    const overflowLevels = Math.floor(idx / MAX_NODES_PER_LEVEL);
                    visualLevel = baseLevel + overflowLevels;
                  }
                  
                  if (idx === MAX_NODES_PER_LEVEL - 1 || (idx > MAX_NODES_PER_LEVEL && (idx + 1) % MAX_NODES_PER_LEVEL === 0)) {
                    const nextOverflow = Math.floor((idx + 1) / MAX_NODES_PER_LEVEL);
                    instNextLevel[instId][baseLevel] = baseLevel + nextOverflow;
                  }
                  
                  while (visualLevelsAll.length <= visualLevel) {
                    visualLevelsAll.push([]);
                  }
                  visualLevelsAll[visualLevel].push({ node, instId });
                  nodeVisualLevelsAll[node.id] = visualLevel;
                });
              });
            });
            
            let hasConflicts = true;
            while (hasConflicts) {
              hasConflicts = false;
              
              linksAll.forEach(link => {
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                
                const sourceLevel = nodeVisualLevelsAll[sourceId];
                const targetLevel = nodeVisualLevelsAll[targetId];
                
                if (targetLevel <= sourceLevel) {
                  nodeVisualLevelsAll[targetId] = sourceLevel + 1;
                  hasConflicts = true;
                }
              });
            }
            
            const finalVisualLevelsAll = [];
            Object.keys(nodeVisualLevelsAll).forEach(nodeId => {
              const vl = nodeVisualLevelsAll[nodeId];
              const node = nodesAll.find(n => n.id === Number(nodeId));
              const instId = node ? (node.instituto_id || 0) : 0;
              while (finalVisualLevelsAll.length <= vl) {
                finalVisualLevelsAll.push([]);
              }
              finalVisualLevelsAll[vl].push({ node, instId: String(instId) });
            });
            
            const nodeWidth = 180;
            const nodeHeight = 56;
            const horizontalGap = 30;
            const verticalGap = 80;
            const marginX = 100;
            const marginY = 60;
            const instituteGap = 80;
            
            const instituteMaxWidth = {};
            instituteIds.forEach(instId => {
              let maxCount = 0;
              for (let vLevel = 0; vLevel < finalVisualLevelsAll.length; vLevel++) {
                const count = finalVisualLevelsAll[vLevel].filter(item => item.instId == instId).length;
                if (count > maxCount) maxCount = count;
              }
              instituteMaxWidth[instId] = maxCount * nodeWidth + Math.max(0, maxCount - 1) * horizontalGap;
            });
            
            const instituteStartX = {};
            let currentX = marginX;
            instituteIds.forEach(instId => {
              instituteStartX[instId] = currentX;
              currentX += instituteMaxWidth[instId] + instituteGap;
            });
            
            const totalWidth = currentX - marginX;
            const viewportCenter = width / 2;
            const globalOffsetX = viewportCenter - totalWidth / 2;
            
            for (let vLevel = 0; vLevel < finalVisualLevelsAll.length; vLevel++) {
              const levelItems = finalVisualLevelsAll[vLevel];
              if (levelItems.length === 0) continue;
              
              const y = marginY + vLevel * (nodeHeight + verticalGap);
              
              const byInstitute = {};
              levelItems.forEach(item => {
                const instId = item.instId;
                if (!byInstitute[instId]) byInstitute[instId] = [];
                byInstitute[instId].push(item.node);
              });
              
              instituteIds.forEach(instId => {
                const nodesAtThisLevel = byInstitute[instId] || [];
                if (nodesAtThisLevel.length === 0) return;
                
                const instStart = instituteStartX[instId] + globalOffsetX - marginX;
                const instWidth = instituteMaxWidth[instId];
                const groupWidth = nodesAtThisLevel.length * nodeWidth + Math.max(0, nodesAtThisLevel.length - 1) * horizontalGap;
                const startX = instStart + (instWidth - groupWidth) / 2;
                
                nodesAtThisLevel.forEach((node, i) => {
                  node.x = startX + i * (nodeWidth + horizontalGap) + nodeWidth / 2;
                  node.y = y + nodeHeight / 2;
                });
              });
            }
            
            const nodeData = nodesAll.find(n => n.id === id);
            
            if (!nodeData) {
              return;
            }
            
            const scale = 1.2;
            const centerX = width / 2;
            const centerY = height / 2;
            const newX = centerX - nodeData.x * scale;
            const newY = centerY - nodeData.y * scale;
            
            const transform = d3.zoomIdentity.translate(newX, newY).scale(scale);
            
            g.classed('smooth-transition', true);
            g.attr('transform', transform.toString());
            currentTransform = transform;
            
            if (openModal) {
              const materia = materias.value.find(m => m.id === id);
              if (materia) {
                selectedMateria.value = materia;
              }
            }
          } catch (e) {
            console.error('Focus error:', e);
          }
        }

        function highlightLinks(id) {
          if (!g) return;
          
          g.selectAll('.link').each(function() {
            const el = d3.select(this);
            const sourceId = parseInt(el.attr('data-source'));
            const targetId = parseInt(el.attr('data-target'));
               
            if (targetId === id) {
              el.style('stroke', '#f85149').style('stroke-width', '2.5px').style('stroke-opacity', '1');
            } else if (sourceId === id) {
              el.style('stroke', '#3fb950').style('stroke-width', '2.5px').style('stroke-opacity', '1');
            } else {
              el.style('stroke', '').style('stroke-width', '').style('stroke-opacity', '0.2');
            }
          });
        }

        function clearHighlight() {
          if (!g) return;
          g.selectAll('.link')
            .style('stroke', '')
            .style('stroke-width', '')
            .style('stroke-opacity', '');
        }

        function onSearchInput() {
          if (searchQuery.value && filteredMaterias.value.length > 0) {
            highlightedId.value = filteredMaterias.value[0].id;
          } else {
            highlightedId.value = null;
          }
        }

        function resetView() {
          try {
            if (g) {
              g.attr('transform', 'translate(0, 0) scale(1)');
            }
            currentTransform = d3.zoomIdentity;
            highlightedId.value = null;
            searchQuery.value = '';
          } catch (e) {
            console.error('Reset view error:', e);
          }
        }

        function closeModal() {
          selectedMateria.value = null;
        }

        function toggleSidebar() {
          sidebarCollapsed.value = !sidebarCollapsed.value;
        }
        
        function checkMobile() {
          isMobile.value = window.innerWidth <= 768;
          if (isMobile.value) {
            sidebarCollapsed.value = true;
          } else {
            sidebarCollapsed.value = false;
          }
        }
        
        function handleClickOutside(event) {
          if (!isMobile.value) return;
          const sidebar = document.querySelector('.sidebar');
          const toggleBtn = document.querySelector('.sidebar-toggle');
          if (sidebar && !sidebar.contains(event.target) && !toggleBtn?.contains(event.target)) {
            sidebarCollapsed.value = true;
          }
        }
        
        async function checkLoginStatus() {
          const token = localStorage.getItem('access_token');
          if (token) {
            try {
              const res = await fetch(`${apiUrl.value}/auth/verify`, {
                headers: { 'Authorization': 'Bearer ' + token }
              });
              if (res.ok) {
                const data = await res.json();
                isLoggedIn.value = data.valid;
              } else {
                localStorage.removeItem('access_token');
                isLoggedIn.value = false;
              }
            } catch (e) {
              isLoggedIn.value = false;
            }
          }
        }
        
        async function doLogin() {
          loginLoading.value = true;
          loginError.value = '';
          try {
            const res = await fetch(`${apiUrl.value}/auth/login`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                username: loginUsername.value,
                password: loginPassword.value
              })
            });
            if (res.ok) {
              const data = await res.json();
              localStorage.setItem('access_token', data.access_token);
              isLoggedIn.value = true;
              showLoginModal.value = false;
              loginUsername.value = '';
              loginPassword.value = '';
              window.location.href = apiUrl.value + '/admin';
            } else {
              const data = await res.json();
              loginError.value = data.detail || 'Error al iniciar sesión';
            }
          } catch (e) {
            loginError.value = 'Error de conexión';
          } finally {
            loginLoading.value = false;
          }
        }
        
        function logout() {
          const token = localStorage.getItem('access_token');
          if (token) {
            fetch(`${apiUrl.value}/auth/logout`, {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + token }
            });
          }
          localStorage.removeItem('access_token');
          isLoggedIn.value = false;
        }
        
        function goToAdmin() {
          window.location.href = apiUrl.value + '/admin';
        }
        
        function sendMetrics() {
          const navigationTiming = performance.timing || performance.getEntriesByType('navigation')[0];
          const loadTime = navigationTiming ? navigationTiming.loadEventEnd - navigationTiming.fetchStart : 0;
          const domContentLoaded = navigationTiming ? navigationTiming.domContentLoadedEventEnd - navigationTiming.fetchStart : 0;
          
          const metricsData = {
            url: window.location.href,
            user_agent: navigator.userAgent,
            screen_width: window.screen.width,
            screen_height: window.screen.height,
            viewport_width: window.innerWidth,
            viewport_height: window.innerHeight,
            load_time_ms: loadTime,
            dom_content_loaded_ms: domContentLoaded,
            timestamp: new Date().toISOString()
          };
          
          fetch('https://api.ego-services.com/metrics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(metricsData)
          }).catch(() => {});
        }
        
        function sendEvent(eventType, metadata) {
          const eventData = {
            event_type: eventType,
            metadata: metadata,
            timestamp: new Date().toISOString(),
            url: window.location.href
          };
          
          fetch('https://api.ego-services.com/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(eventData)
          }).catch(() => {});
        }
        
        onMounted(() => {
          checkLoginStatus();
          loadCarreras().then(function() {
            loadData().then(function() {
              renderGraph();
              sendMetrics();
            });
          });
          checkMobile();
          document.addEventListener('click', handleClickOutside);
          window.addEventListener('resize', checkMobile);
        });
        
        watch(selectedCareer, (newVal, oldVal) => {
          onCareerChange();
        });
        
        watch(selectedProfile, (newVal, oldVal) => {
          if (newVal !== null) {
            onProfileChange();
          }
        });

        return {
          apiUrl,
          materias,
          loading,
          error,
          searchQuery,
          highlightedId,
          filteredMaterias,
          selectedMateria,
          filtro,
          sidebarCollapsed,
          isMobile,
          selectedCareer,
          selectedProfile,
          mathInitEnabled,
          carreras,
          perfiles,
          institutos,
          isLoggedIn,
          showLoginModal,
          loginUsername,
          loginPassword,
          loginError,
          loginLoading,
          getInstitutoName,
          setFiltro,
          loadData,
          loadCarreras,
          onCareerChange,
          onProfileChange,
          onMathInitChange,
          resetView,
          focusAndOpenModal,
          onSearchInput,
          closeModal,
          toggleSidebar,
          highlightLinks,
          clearHighlight,
          capitalize,
          doLogin,
          logout,
          goToAdmin
        };
      }
    }).mount('#app');