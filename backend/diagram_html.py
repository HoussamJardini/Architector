from handlers import get_current_schema

# Dark theme color schemes with orange accent
COLORS = [
    {"bg": "#ff6b2c", "light": "#ff8c42", "text": "#ffffff"},  # Orange
    {"bg": "#3b82f6", "light": "#60a5fa", "text": "#ffffff"},  # Blue
    {"bg": "#8b5cf6", "light": "#a78bfa", "text": "#ffffff"},  # Purple
    {"bg": "#14b8a6", "light": "#2dd4bf", "text": "#ffffff"},  # Teal
    {"bg": "#ec4899", "light": "#f472b6", "text": "#ffffff"},  # Pink
    {"bg": "#f59e0b", "light": "#fbbf24", "text": "#ffffff"},  # Amber
]

def get_entity_positions(entities: list) -> dict:
    """Calculate positions for entities in a grid layout"""
    positions = {}
    count = len(entities)
    cols = min(3, count)
    
    x_spacing = 320
    y_spacing = 280
    start_x = 150
    start_y = 150
    
    for i, entity in enumerate(entities):
        row = i // cols
        col = i % cols
        offset_x = (row % 2) * 40
        
        positions[entity.name] = {
            "x": start_x + col * x_spacing + offset_x,
            "y": start_y + row * y_spacing,
            "color": COLORS[i % len(COLORS)]
        }
    
    return positions


def generate_entity_svg(entity, position: dict, index: int) -> str:
    """Generate SVG for a single entity (draggable)"""
    x = position["x"]
    y = position["y"]
    color = position["color"]
    
    attr_count = len(entity.attributes)
    box_height = 54 + attr_count * 32
    box_width = 240
    header_height = 48
    
    svg = f'''
    <g class="entity" data-entity="{entity.name}" data-x="{x}" data-y="{y}" transform="translate({x}, {y})" style="cursor: grab;">
        <!-- Shadow -->
        <rect x="4" y="4" width="{box_width}" height="{box_height}" 
              rx="14" fill="rgba(0,0,0,0.4)"/>
        
        <!-- Main box -->
        <rect class="entity-bg" x="0" y="0" width="{box_width}" height="{box_height}" 
              rx="14" fill="#1a1a25" stroke="{color['bg']}" stroke-width="2"/>
        
        <!-- Header -->
        <rect x="0" y="0" width="{box_width}" height="{header_height}" 
              rx="14" fill="{color['bg']}"/>
        <rect x="0" y="{header_height - 14}" width="{box_width}" height="14" 
              fill="{color['bg']}"/>
        
        <!-- Entity name -->
        <text x="{box_width/2}" y="32" 
              text-anchor="middle" fill="{color['text']}" 
              font-weight="700" font-size="15" font-family="Inter, system-ui, sans-serif">{entity.name}</text>
        
        <!-- Divider line -->
        <line x1="0" y1="{header_height}" x2="{box_width}" y2="{header_height}" 
              stroke="{color['bg']}" stroke-width="1" opacity="0.3"/>
    '''
    
    for i, attr in enumerate(entity.attributes):
        attr_y = header_height + 26 + i * 32
        
        if attr.primary_key:
            key_icon = f'''<text x="16" y="{attr_y}" font-size="12" fill="#ff6b2c">🔑</text>'''
        elif attr.unique:
            key_icon = f'''<text x="16" y="{attr_y}" font-size="12" fill="#8b5cf6">◆</text>'''
        else:
            key_icon = f'''<circle cx="20" cy="{attr_y - 4}" r="4" fill="{color['bg']}" opacity="0.6"/>'''
        
        svg += f'''
        {key_icon}
        <text x="38" y="{attr_y}" font-size="13" fill="#e2e8f0" font-family="Inter, system-ui, sans-serif">{attr.name}</text>
        <text x="{box_width - 16}" y="{attr_y}" text-anchor="end" 
              font-size="11" fill="#6b7280" font-family="Inter, system-ui, sans-serif">{attr.type[:15]}</text>
        '''
    
    svg += '</g>'
    return svg, box_width, box_height


def generate_relationship_svg(rel, positions: dict, entity_heights: dict) -> str:
    """Generate SVG for a relationship line"""
    from_pos = positions.get(rel.from_entity)
    to_pos = positions.get(rel.to_entity)
    
    if not from_pos or not to_pos:
        return ""
    
    box_width = 240
    
    from_x = from_pos["x"] + box_width / 2
    from_y = from_pos["y"] + entity_heights.get(rel.from_entity, 100)
    
    to_x = to_pos["x"] + box_width / 2
    to_y = to_pos["y"]
    
    if abs(from_pos["y"] - to_pos["y"]) < 50:
        if from_pos["x"] < to_pos["x"]:
            from_x = from_pos["x"] + box_width
            to_x = to_pos["x"]
        else:
            from_x = from_pos["x"]
            to_x = to_pos["x"] + box_width
        from_y = from_pos["y"] + entity_heights.get(rel.from_entity, 100) / 2
        to_y = to_pos["y"] + entity_heights.get(rel.to_entity, 100) / 2
    
    mid_y = (from_y + to_y) / 2
    
    if rel.type == "one-to-one":
        from_symbol, to_symbol = "1", "1"
    elif rel.type == "one-to-many":
        from_symbol, to_symbol = "1", "∞"
    elif rel.type == "many-to-one":
        from_symbol, to_symbol = "∞", "1"
    else:
        from_symbol, to_symbol = "∞", "∞"
    
    color = "#ff6b2c"
    
    svg = f'''
    <g class="relationship" data-from="{rel.from_entity}" data-to="{rel.to_entity}">
        <!-- Connection line -->
        <path class="rel-path" d="M {from_x} {from_y} C {from_x} {mid_y}, {to_x} {mid_y}, {to_x} {to_y}" 
              stroke="{color}" stroke-width="2" fill="none" 
              stroke-dasharray="6,4" opacity="0.7"/>
        
        <!-- Relationship label -->
        <rect x="{(from_x + to_x) / 2 - 45}" y="{mid_y - 14}" 
              width="90" height="28" rx="14" fill="#1a1a25" stroke="{color}" stroke-width="1"/>
        <text x="{(from_x + to_x) / 2}" y="{mid_y + 5}" 
              text-anchor="middle" font-size="11" fill="{color}" font-weight="600" 
              font-family="Inter, system-ui, sans-serif">{rel.name}</text>
        
        <!-- Cardinality symbols -->
        <circle cx="{from_x}" cy="{from_y + 20}" r="14" fill="#1a1a25" stroke="{color}" stroke-width="1"/>
        <text x="{from_x}" y="{from_y + 25}" text-anchor="middle" 
              font-size="13" fill="{color}" font-weight="600">{from_symbol}</text>
        
        <circle cx="{to_x}" cy="{to_y - 20}" r="14" fill="#1a1a25" stroke="{color}" stroke-width="1"/>
        <text x="{to_x}" y="{to_y - 15}" text-anchor="middle" 
              font-size="13" fill="{color}" font-weight="600">{to_symbol}</text>
    </g>
    '''
    return svg


def schema_to_interactive_html() -> str:
    """Convert current schema to interactive HTML with zoom/pan and draggable entities"""
    schema = get_current_schema()
    
    if schema is None:
        return "<p>No schema to display.</p>"
    
    positions = get_entity_positions(schema.entities)
    
    entity_svgs = []
    entity_heights = {}
    
    for i, entity in enumerate(schema.entities):
        svg, width, height = generate_entity_svg(entity, positions[entity.name], i)
        entity_svgs.append(svg)
        entity_heights[entity.name] = height
    
    relationship_svgs = []
    for rel in schema.relationships:
        svg = generate_relationship_svg(rel, positions, entity_heights)
        relationship_svgs.append(svg)
    
    # Much larger canvas for more room to move entities
    canvas_width = 3000
    canvas_height = 2000
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                background: #0a0a0f;
                overflow: hidden;
                font-family: 'Inter', system-ui, sans-serif;
            }}
            
            .container {{
                width: 100%;
                height: 100vh;
                overflow: hidden;
                cursor: grab;
                position: relative;
            }}
            
            .container:active {{
                cursor: grabbing;
            }}
            
            .container.dragging-entity {{
                cursor: grabbing;
            }}
            
            .controls {{
                position: fixed;
                top: 12px;
                right: 12px;
                display: flex;
                gap: 8px;
                z-index: 1000;
            }}
            
            .control-btn {{
                width: 38px;
                height: 38px;
                border-radius: 10px;
                border: 1px solid #2a2a3a;
                background: #16161f;
                color: #a0a0b0;
                cursor: pointer;
                font-size: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
            }}
            
            .control-btn:hover {{
                background: rgba(255, 107, 44, 0.1);
                border-color: #ff6b2c;
                color: #ff6b2c;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(255, 107, 44, 0.2);
            }}
            
            .zoom-level {{
                position: fixed;
                bottom: 12px;
                left: 12px;
                background: #16161f;
                border: 1px solid #2a2a3a;
                padding: 8px 14px;
                border-radius: 10px;
                font-size: 12px;
                color: #ff6b2c;
                font-weight: 600;
            }}
            
            .title {{
                position: fixed;
                top: 12px;
                left: 12px;
                background: linear-gradient(135deg, #ff6b2c 0%, #ff8c42 100%);
                color: white;
                padding: 10px 18px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
                box-shadow: 0 4px 15px rgba(255, 107, 44, 0.3);
            }}
            
            #svg-container {{
                transform-origin: 0 0;
                transition: transform 0.1s ease-out;
            }}
            
            .entity {{
                cursor: grab;
                transition: filter 0.2s ease;
            }}
            
            .entity:hover {{
                filter: brightness(1.1);
            }}
            
            .entity.dragging {{
                cursor: grabbing;
                filter: brightness(1.2);
            }}
            
            .entity.dragging .entity-bg {{
                stroke-width: 3;
            }}
            
            .help-text {{
                position: fixed;
                bottom: 12px;
                right: 12px;
                background: #16161f;
                border: 1px solid #2a2a3a;
                padding: 8px 14px;
                border-radius: 10px;
                font-size: 11px;
                color: #6b7280;
            }}
        </style>
    </head>
    <body>
        <div class="title">📊 {schema.schema_name}</div>
        
        <div class="controls">
            <button class="control-btn" onclick="zoomIn()" title="Zoom In">+</button>
            <button class="control-btn" onclick="zoomOut()" title="Zoom Out">−</button>
            <button class="control-btn" onclick="resetView()" title="Reset View">⌂</button>
            <button class="control-btn" onclick="fitToScreen()" title="Fit to Screen">◻</button>
        </div>
        
        <div class="zoom-level" id="zoom-level">100%</div>
        <div class="help-text">Drag tables to rearrange • Scroll to zoom • Drag background to pan</div>
        
        <div class="container" id="container">
            <svg id="svg-container" width="{canvas_width}" height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}">
                <!-- Background pattern -->
                <defs>
                    <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                        <circle cx="25" cy="25" r="1" fill="#2a2a3a" opacity="0.4"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)"/>
                
                <!-- Relationships (drawn first, behind entities) -->
                <g id="relationships-layer">
                    {"".join(relationship_svgs)}
                </g>
                
                <!-- Entities -->
                <g id="entities-layer">
                    {"".join(entity_svgs)}
                </g>
            </svg>
        </div>
        
        <script>
            const container = document.getElementById('container');
            const svgContainer = document.getElementById('svg-container');
            const zoomLevelDisplay = document.getElementById('zoom-level');
            
            let scale = 1;
            let translateX = 0;
            let translateY = 0;
            let isPanning = false;
            let startX, startY;
            
            // Entity dragging
            let isDraggingEntity = false;
            let draggedEntity = null;
            let entityStartX, entityStartY;
            let entityOffsetX, entityOffsetY;
            
            // Store entity positions
            const entityPositions = {{}};
            document.querySelectorAll('.entity').forEach(entity => {{
                const name = entity.dataset.entity;
                entityPositions[name] = {{
                    x: parseFloat(entity.dataset.x),
                    y: parseFloat(entity.dataset.y)
                }};
            }});
            
            function applyTransform() {{
                svgContainer.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
                zoomLevelDisplay.textContent = Math.round(scale * 100) + '%';
            }}
            
            function zoomIn() {{
                scale = Math.min(scale * 1.25, 4);
                applyTransform();
            }}
            
            function zoomOut() {{
                scale = Math.max(scale / 1.25, 0.2);
                applyTransform();
            }}
            
            function resetView() {{
                scale = 1;
                translateX = 0;
                translateY = 0;
                applyTransform();
            }}
            
            function fitToScreen() {{
                const entities = document.querySelectorAll('.entity');
                if (entities.length === 0) return;
                
                let minX = Infinity, minY = Infinity, maxX = 0, maxY = 0;
                
                entities.forEach(entity => {{
                    const name = entity.dataset.entity;
                    const pos = entityPositions[name];
                    const bbox = entity.getBBox();
                    minX = Math.min(minX, pos.x);
                    minY = Math.min(minY, pos.y);
                    maxX = Math.max(maxX, pos.x + bbox.width);
                    maxY = Math.max(maxY, pos.y + bbox.height);
                }});
                
                const contentWidth = maxX - minX + 100;
                const contentHeight = maxY - minY + 100;
                const containerRect = container.getBoundingClientRect();
                
                scale = Math.min(
                    containerRect.width / contentWidth,
                    containerRect.height / contentHeight,
                    1.5
                ) * 0.85;
                
                translateX = (containerRect.width - contentWidth * scale) / 2 - minX * scale + 50;
                translateY = (containerRect.height - contentHeight * scale) / 2 - minY * scale + 50;
                
                applyTransform();
            }}
            
            // Mouse wheel zoom
            container.addEventListener('wheel', (e) => {{
                e.preventDefault();
                
                const rect = container.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                const oldScale = scale;
                
                if (e.deltaY < 0) {{
                    scale = Math.min(scale * 1.1, 4);
                }} else {{
                    scale = Math.max(scale / 1.1, 0.2);
                }}
                
                const scaleChange = scale / oldScale;
                translateX = mouseX - (mouseX - translateX) * scaleChange;
                translateY = mouseY - (mouseY - translateY) * scaleChange;
                
                applyTransform();
            }});
            
            // Entity dragging
            document.querySelectorAll('.entity').forEach(entity => {{
                entity.addEventListener('mousedown', (e) => {{
                    e.stopPropagation();
                    isDraggingEntity = true;
                    draggedEntity = entity;
                    container.classList.add('dragging-entity');
                    entity.classList.add('dragging');
                    
                    const name = entity.dataset.entity;
                    entityStartX = entityPositions[name].x;
                    entityStartY = entityPositions[name].y;
                    
                    entityOffsetX = (e.clientX - translateX) / scale - entityStartX;
                    entityOffsetY = (e.clientY - translateY) / scale - entityStartY;
                }});
            }});
            
            // Pan with mouse drag (on background)
            container.addEventListener('mousedown', (e) => {{
                if (isDraggingEntity) return;
                isPanning = true;
                startX = e.clientX - translateX;
                startY = e.clientY - translateY;
                container.style.cursor = 'grabbing';
            }});
            
            document.addEventListener('mousemove', (e) => {{
                if (isDraggingEntity && draggedEntity) {{
                    const newX = (e.clientX - translateX) / scale - entityOffsetX;
                    const newY = (e.clientY - translateY) / scale - entityOffsetY;
                    
                    const name = draggedEntity.dataset.entity;
                    entityPositions[name].x = newX;
                    entityPositions[name].y = newY;
                    
                    draggedEntity.setAttribute('transform', `translate(${{newX}}, ${{newY}})`);
                    updateRelationships();
                    return;
                }}
                
                if (!isPanning) return;
                
                translateX = e.clientX - startX;
                translateY = e.clientY - startY;
                applyTransform();
            }});
            
            document.addEventListener('mouseup', () => {{
                if (isDraggingEntity && draggedEntity) {{
                    draggedEntity.classList.remove('dragging');
                    container.classList.remove('dragging-entity');
                }}
                isDraggingEntity = false;
                draggedEntity = null;
                isPanning = false;
                container.style.cursor = 'grab';
            }});
            
            function updateRelationships() {{
                document.querySelectorAll('.relationship').forEach(rel => {{
                    const fromName = rel.dataset.from;
                    const toName = rel.dataset.to;
                    
                    const fromPos = entityPositions[fromName];
                    const toPos = entityPositions[toName];
                    
                    if (!fromPos || !toPos) return;
                    
                    const boxWidth = 240;
                    const fromEntity = document.querySelector(`.entity[data-entity="${{fromName}}"]`);
                    const toEntity = document.querySelector(`.entity[data-entity="${{toName}}"]`);
                    
                    const fromHeight = fromEntity ? fromEntity.getBBox().height : 150;
                    const toHeight = toEntity ? toEntity.getBBox().height : 150;
                    
                    let fromX = fromPos.x + boxWidth / 2;
                    let fromY = fromPos.y + fromHeight;
                    let toX = toPos.x + boxWidth / 2;
                    let toY = toPos.y;
                    
                    if (Math.abs(fromPos.y - toPos.y) < 50) {{
                        if (fromPos.x < toPos.x) {{
                            fromX = fromPos.x + boxWidth;
                            toX = toPos.x;
                        }} else {{
                            fromX = fromPos.x;
                            toX = toPos.x + boxWidth;
                        }}
                        fromY = fromPos.y + fromHeight / 2;
                        toY = toPos.y + toHeight / 2;
                    }}
                    
                    const midY = (fromY + toY) / 2;
                    
                    const path = rel.querySelector('.rel-path');
                    if (path) {{
                        path.setAttribute('d', `M ${{fromX}} ${{fromY}} C ${{fromX}} ${{midY}}, ${{toX}} ${{midY}}, ${{toX}} ${{toY}}`);
                    }}
                    
                    // Update label position
                    const rects = rel.querySelectorAll('rect');
                    const texts = rel.querySelectorAll('text');
                    
                    if (rects.length >= 1) {{
                        rects[0].setAttribute('x', (fromX + toX) / 2 - 45);
                        rects[0].setAttribute('y', midY - 14);
                    }}
                    
                    if (texts.length >= 1) {{
                        texts[0].setAttribute('x', (fromX + toX) / 2);
                        texts[0].setAttribute('y', midY + 5);
                    }}
                    
                    // Update cardinality circles
                    const circles = rel.querySelectorAll('circle');
                    if (circles.length >= 2) {{
                        circles[0].setAttribute('cx', fromX);
                        circles[0].setAttribute('cy', fromY + 20);
                        circles[1].setAttribute('cx', toX);
                        circles[1].setAttribute('cy', toY - 20);
                    }}
                    
                    if (texts.length >= 3) {{
                        texts[1].setAttribute('x', fromX);
                        texts[1].setAttribute('y', fromY + 25);
                        texts[2].setAttribute('x', toX);
                        texts[2].setAttribute('y', toY - 15);
                    }}
                }});
            }}
            
            // Touch support
            let lastTouchDistance = 0;
            
            container.addEventListener('touchstart', (e) => {{
                if (e.touches.length === 1) {{
                    isPanning = true;
                    startX = e.touches[0].clientX - translateX;
                    startY = e.touches[0].clientY - translateY;
                }} else if (e.touches.length === 2) {{
                    lastTouchDistance = Math.hypot(
                        e.touches[0].clientX - e.touches[1].clientX,
                        e.touches[0].clientY - e.touches[1].clientY
                    );
                }}
            }});
            
            container.addEventListener('touchmove', (e) => {{
                e.preventDefault();
                
                if (e.touches.length === 1 && isPanning) {{
                    translateX = e.touches[0].clientX - startX;
                    translateY = e.touches[0].clientY - startY;
                    applyTransform();
                }} else if (e.touches.length === 2) {{
                    const distance = Math.hypot(
                        e.touches[0].clientX - e.touches[1].clientX,
                        e.touches[0].clientY - e.touches[1].clientY
                    );
                    
                    if (lastTouchDistance > 0) {{
                        const scaleChange = distance / lastTouchDistance;
                        scale = Math.max(0.2, Math.min(4, scale * scaleChange));
                        applyTransform();
                    }}
                    
                    lastTouchDistance = distance;
                }}
            }});
            
            container.addEventListener('touchend', () => {{
                isPanning = false;
                lastTouchDistance = 0;
            }});
            
            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {{
                if (e.key === '+' || e.key === '=') zoomIn();
                if (e.key === '-') zoomOut();
                if (e.key === '0') resetView();
                if (e.key === 'f' || e.key === 'F') fitToScreen();
            }});
            
            // Auto fit on load
            setTimeout(fitToScreen, 100);
        </script>
    </body>
    </html>
    '''
    
    return html
