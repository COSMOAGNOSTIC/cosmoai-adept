extends Node2D
##
## Real-time spatial visualizer for agent_core - "Circuit" skin.
##
## Connects to the WebSocket server agent_core.events opens on
## ws://localhost:8080 and renders every model call / tool call as a
## pulsing core walking a circuit board to the node for whichever tool
## it's calling, with a HUD-style speech bubble showing what it's doing.

const RECONNECT_INTERVAL := 2.0
const MIN_BUBBLE_TIME := 3.0   # seconds - even "done" needs to be readable
const MAX_BUBBLE_TIME := 7.0
const CHARS_PER_SECOND := 12.0  # ~ comfortable reading speed

var socket := WebSocketPeer.new()
var reconnect_timer := 0.0
var connected := false

var stations := {}          # name -> Vector2 position
var station_colors := {}    # name -> Color
var trace_lines := {}       # name -> Line2D (agent -> station, circuit-jog)
var agent: Node2D
var agent_core_shape: Polygon2D
var bubble_panel: PanelContainer
var bubble_label: Label
var bubble_timer := 0.0

const TOOL_STATION := {
	"get_weather": "WEATHER",
	"assemble_digest": "DIGEST_DESK",
	"write_log": "LOG",
	"read_pending": "LOG",
	"add_pending": "LOG",
	"complete_pending": "LOG",
	"read_file": "FILES",
	"write_file": "FILES",
	"list_files": "FILES",
}

const STATION_LAYOUT := {
	"MODEL": Vector2(480, 270),
	"WEATHER": Vector2(150, 110),
	"DIGEST_DESK": Vector2(810, 110),
	"LOG": Vector2(150, 430),
	"FILES": Vector2(810, 430),
	"APPROVAL": Vector2(480, 470),
}

const STATION_COLOR := {
	"MODEL": Color("5ac8ff"),
	"WEATHER": Color("78ffaa"),
	"DIGEST_DESK": Color("ffd25a"),
	"LOG": Color("c878ff"),
	"FILES": Color("ff6464"),
	"APPROVAL": Color("ff9d42"),
}


func _ready() -> void:
	RenderingServer.set_default_clear_color(Color("06090f"))
	_build_background()
	_build_stations()
	_build_trace_lines()
	_build_agent()
	_build_bubble()
	_build_scanlines()
	_build_hud_text()
	_connect_socket()


func _build_background() -> void:
	var bg := TextureRect.new()
	bg.texture = load("res://assets/bg_circuit.png")
	bg.size = Vector2(960, 540)
	bg.z_index = -10
	add_child(bg)


func _build_stations() -> void:
	var glow_tex := load("res://assets/node_glow.png")
	for key in STATION_LAYOUT.keys():
		var pos: Vector2 = STATION_LAYOUT[key]
		var color: Color = STATION_COLOR[key]
		stations[key] = pos
		station_colors[key] = color

		var glow := Sprite2D.new()
		glow.texture = glow_tex
		glow.position = pos
		glow.modulate = Color(color.r, color.g, color.b, 0.55)
		glow.scale = Vector2(0.6, 0.6)
		add_child(glow)

		var ring := Node2D.new()
		ring.position = pos
		add_child(ring)
		var ring_draw := _RingDraw.new()
		ring_draw.ring_color = color
		ring.add_child(ring_draw)

		var label := Label.new()
		label.text = key.replace("_", " ")
		label.add_theme_color_override("font_color", color)
		label.position = pos + Vector2(-70, 30)
		label.size = Vector2(140, 20)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		add_child(label)


func _build_trace_lines() -> void:
	for key in STATION_LAYOUT.keys():
		if key == "MODEL":
			continue
		var line := Line2D.new()
		line.width = 2.0
		line.default_color = Color(station_colors[key].r, station_colors[key].g, station_colors[key].b, 0.35)
		add_child(line)
		trace_lines[key] = line
	_update_trace_lines(STATION_LAYOUT["MODEL"])


func _update_trace_lines(agent_pos: Vector2) -> void:
	for key in trace_lines.keys():
		var target: Vector2 = stations[key]
		var jog := Vector2(target.x, agent_pos.y)
		var line: Line2D = trace_lines[key]
		line.points = PackedVector2Array([agent_pos, jog, target])


func _build_agent() -> void:
	agent = Node2D.new()
	agent.position = STATION_LAYOUT["MODEL"]
	add_child(agent)

	var glow := Sprite2D.new()
	glow.texture = load("res://assets/node_glow.png")
	glow.modulate = Color(0.55, 0.85, 1.0, 0.7)
	glow.scale = Vector2(0.85, 0.85)
	agent.add_child(glow)

	agent_core_shape = Polygon2D.new()
	var r := 15.0
	agent_core_shape.polygon = PackedVector2Array([
		Vector2(0, -r), Vector2(r, 0), Vector2(0, r), Vector2(-r, 0)
	])
	agent_core_shape.color = Color("e6faff")
	agent.add_child(agent_core_shape)


func _build_bubble() -> void:
	bubble_panel = PanelContainer.new()
	bubble_panel.visible = false
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.04, 0.06, 0.1, 0.92)
	style.border_color = Color("5ac8ff")
	style.border_width_left = 2
	style.border_width_right = 2
	style.border_width_top = 2
	style.border_width_bottom = 2
	style.corner_radius_top_left = 4
	style.corner_radius_top_right = 4
	style.corner_radius_bottom_left = 4
	style.corner_radius_bottom_right = 4
	style.content_margin_left = 10
	style.content_margin_right = 10
	style.content_margin_top = 6
	style.content_margin_bottom = 6
	bubble_panel.add_theme_stylebox_override("panel", style)
	bubble_panel.custom_minimum_size = Vector2(240, 0)

	bubble_label = Label.new()
	bubble_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	bubble_label.add_theme_color_override("font_color", Color("9be8ff"))
	bubble_panel.add_child(bubble_label)
	add_child(bubble_panel)


func _build_scanlines() -> void:
	var scan := TextureRect.new()
	scan.texture = load("res://assets/scanlines.png")
	scan.size = Vector2(960, 540)
	scan.z_index = 10
	scan.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(scan)


func _build_hud_text() -> void:
	var title := Label.new()
	title.text = "AGENT_CORE // LIVE TELEMETRY"
	title.position = Vector2(16, 10)
	title.add_theme_color_override("font_color", Color("78d4ff"))
	add_child(title)

	var status := Label.new()
	status.text = "ws://localhost:8080"
	status.position = Vector2(16, 512)
	status.add_theme_color_override("font_color", Color("4a7a90"))
	add_child(status)


func _connect_socket() -> void:
	var err := socket.connect_to_url("ws://localhost:8080")
	if err != OK:
		push_warning("visualizer: could not start connection: %s" % err)


func _process(delta: float) -> void:
	socket.poll()
	var state := socket.get_ready_state()

	if state == WebSocketPeer.STATE_OPEN:
		connected = true
		while socket.get_available_packet_count() > 0:
			var packet := socket.get_packet().get_string_from_utf8()
			_handle_event(packet)
	elif state == WebSocketPeer.STATE_CLOSED:
		if connected:
			connected = false
		reconnect_timer -= delta
		if reconnect_timer <= 0.0:
			reconnect_timer = RECONNECT_INTERVAL
			_connect_socket()

	_update_trace_lines(agent.position)

	if bubble_panel.visible:
		bubble_timer -= delta
		if bubble_timer <= 0.0:
			bubble_panel.visible = false


func _handle_event(raw: String) -> void:
	var parsed = JSON.parse_string(raw)
	if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
		return

	var event_type: String = parsed.get("type", "")
	match event_type:
		"model_start":
			_walk_to("MODEL")
			_say("thinking...")
		"model_end":
			var calls: Array = parsed.get("tool_calls", [])
			if calls.is_empty():
				var text: String = parsed.get("text", "")
				_say(text if text != "" else "responded")
		"tool_start":
			var tool_name: String = parsed.get("tool", "")
			var station: String = TOOL_STATION.get(tool_name, "MODEL")
			_walk_to(station)
			_say("using %s" % tool_name)
		"tool_end":
			var ok: bool = parsed.get("ok", true)
			_say("done" if ok else "error")
		"awaiting_approval":
			var tool_name2: String = parsed.get("tool", "")
			_walk_to("APPROVAL")
			_say("awaiting approval: %s..." % tool_name2)
		"approval_decided":
			var approved: bool = parsed.get("approved", false)
			_say("approved - proceeding" if approved else "denied by human")


func _walk_to(station_key: String) -> void:
	if not stations.has(station_key):
		return
	var target: Vector2 = stations[station_key]
	var tween := create_tween()
	tween.set_trans(Tween.TRANS_SINE)
	tween.tween_property(agent, "position", target, 0.6)


func _say(text: String) -> void:
	bubble_label.text = text
	bubble_panel.position = agent.position + Vector2(-120, -84)
	bubble_panel.visible = true
	# Give the reader enough time regardless of how fast events fire -
	# ~12 chars/sec reading speed, floored so even "done" is legible,
	# capped so a long response doesn't stall the whole scene.
	bubble_timer = clamp(text.length() / CHARS_PER_SECOND, MIN_BUBBLE_TIME, MAX_BUBBLE_TIME)


class _RingDraw extends Node2D:
	var ring_color: Color = Color.WHITE

	func _ready() -> void:
		queue_redraw()

	func _draw() -> void:
		draw_arc(Vector2.ZERO, 22, 0, TAU, 32, ring_color, 3.0)
		draw_circle(Vector2.ZERO, 6, ring_color)
