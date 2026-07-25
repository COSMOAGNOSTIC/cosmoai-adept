extends Node2D
##
## Real-time spatial visualizer for agent_core.
##
## Connects to the WebSocket server agent_core.events opens on
## ws://localhost:8080 and renders every model call / tool call as an
## agent sprite walking across a small top-down office to the matching
## station, with a speech bubble showing what it's doing.
##
## No external assets required - stations and the agent are drawn
## procedurally so this scene runs standalone. Swap in Kenney.nl CC0
## sprites (see README.md in this folder) for a polished look; the
## event-handling logic below doesn't change.

const RECONNECT_INTERVAL := 2.0

var socket := WebSocketPeer.new()
var reconnect_timer := 0.0
var connected := false

var stations := {}          # tool/model name -> Vector2 position
var station_labels := {}    # tool/model name -> Label node
var agent: Node2D
var agent_home: Vector2
var bubble: Label
var bubble_timer := 0.0

# Maps a tool name (as emitted by agent_core.agent) to a station key.
const TOOL_STATION := {
	"get_weather": "Weather",
	"assemble_digest": "Digest Desk",
	"write_log": "Log",
	"read_pending": "Log",
	"add_pending": "Log",
	"complete_pending": "Log",
	"read_file": "Files",
	"write_file": "Files",
	"list_files": "Files",
}

const STATION_COLORS := {
	"Model": Color("5aa9e6"),
	"Weather": Color("6fcf97"),
	"Digest Desk": Color("f2c94c"),
	"Log": Color("bb6bd9"),
	"Files": Color("eb5757"),
}


func _ready() -> void:
	RenderingServer.set_default_clear_color(Color("1b1e26"))
	_build_stations()
	_build_agent()
	_build_bubble()
	_connect_socket()


func _build_stations() -> void:
	var layout := {
		"Model": Vector2(480, 270),
		"Weather": Vector2(180, 120),
		"Digest Desk": Vector2(780, 120),
		"Log": Vector2(180, 420),
		"Files": Vector2(780, 420),
	}
	for key in layout.keys():
		var pos: Vector2 = layout[key]
		stations[key] = pos

		var box := ColorRect.new()
		box.size = Vector2(120, 80)
		box.position = pos - box.size / 2
		box.color = STATION_COLORS.get(key, Color.GRAY)
		box.color.a = 0.35
		add_child(box)

		var label := Label.new()
		label.text = key
		label.position = pos - Vector2(60, 55)
		label.size = Vector2(120, 20)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		add_child(label)
		station_labels[key] = label


func _build_agent() -> void:
	agent_home = stations["Model"]
	agent = Node2D.new()
	agent.position = agent_home
	add_child(agent)

	var body := ColorRect.new()
	body.size = Vector2(28, 28)
	body.position = Vector2(-14, -14)
	body.color = Color("f7f7f7")
	agent.add_child(body)

	var eye := ColorRect.new()
	eye.size = Vector2(8, 8)
	eye.position = Vector2(2, -6)
	eye.color = Color("1b1e26")
	agent.add_child(eye)


func _build_bubble() -> void:
	bubble = Label.new()
	bubble.visible = false
	bubble.size = Vector2(220, 60)
	bubble.autowrap_mode = TextServer.AUTOWRAP_WORD
	bubble.add_theme_color_override("font_color", Color.WHITE)
	add_child(bubble)


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

	if bubble.visible:
		bubble_timer -= delta
		if bubble_timer <= 0.0:
			bubble.visible = false


func _handle_event(raw: String) -> void:
	var parsed = JSON.parse_string(raw)
	if parsed == null or typeof(parsed) != TYPE_DICTIONARY:
		return

	var event_type: String = parsed.get("type", "")
	match event_type:
		"model_start":
			_walk_to("Model")
			_say("thinking...")
		"model_end":
			var calls: Array = parsed.get("tool_calls", [])
			if calls.is_empty():
				var text: String = parsed.get("text", "")
				_say(text if text != "" else "responded")
		"tool_start":
			var tool_name: String = parsed.get("tool", "")
			var station: String = TOOL_STATION.get(tool_name, "Model")
			_walk_to(station)
			_say("using %s" % tool_name)
		"tool_end":
			var ok: bool = parsed.get("ok", true)
			_say("done" if ok else "error")


func _walk_to(station_key: String) -> void:
	if not stations.has(station_key):
		return
	var target: Vector2 = stations[station_key]
	var tween := create_tween()
	tween.set_trans(Tween.TRANS_SINE)
	tween.tween_property(agent, "position", target, 0.6)


func _say(text: String) -> void:
	bubble.text = text
	bubble.position = agent.position + Vector2(-110, -70)
	bubble.visible = true
	bubble_timer = 1.8
