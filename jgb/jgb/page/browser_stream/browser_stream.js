frappe.pages['browser-stream'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Browser Stream',
		single_column: true
	});

	var $bar = $('<div class="browser-stream-bar" style="display:flex;gap:8px;margin-bottom:8px;align-items:center;">');
	var $url = $('<input type="text" class="form-control" placeholder="https://…" style="max-width:480px;">');
	var $status = $('<span style="margin-left:auto;color:#8d99a6;font-size:12px;"></span>');
	['Back', 'Fwd', 'Reload'].forEach(function(label, i) {
		var action = ['back', 'forward', 'reload'][i];
		$bar.append($('<button class="btn btn-default btn-sm">' + label + '</button>')
			.on('click', function() { send(action); }));
	});
	$bar.append($url);
	$bar.append($('<button class="btn btn-primary btn-sm">Go</button>')
		.on('click', function() { send('goto', { url: $url.val() }); }));
	$bar.append($('<button class="btn btn-default btn-sm">Close Tab</button>')
		.on('click', function() {
			frappe.confirm('Close the tab? This clears the browser session.', function() { send('close'); });
		}));
	$bar.append($('<button class="btn btn-default btn-sm">Full Screen</button>')
		.on('click', function() { $stage[0].requestFullscreen(); }));
	$bar.append($status);
	page.body.append($bar);

	var $stage = $('<div class="browser-stream-stage" tabindex="0" style="outline:none;background:#111;overflow:auto;max-height:calc(100vh - 160px);">');
	var $img = $('<img draggable="false" style="display:block;width:100%;height:auto;cursor:crosshair;">');
	$stage.append($img).appendTo(page.body);
	$('<style>.browser-stream-stage:fullscreen{display:flex;align-items:center;justify-content:center;max-height:none}.browser-stream-stage:fullscreen img{width:auto;max-width:100vw;max-height:100vh;}</style>')
		.appendTo(page.body);

	var lastTs = 0;
	function send(action, kw) {
		frappe.call({
			method: 'jgb.browser_stream.command',
			args: Object.assign({ action: action }, kw || {})
		});
	}
	function scale(e) {
		var r = $img[0].getBoundingClientRect();
		return {
			x: (e.clientX - r.left) * (1280 / r.width),
			y: (e.clientY - r.top) * (800 / r.height)
		};
	}
	var lastClick = { t: 0, x: -1, y: -1 };
	$img.on('click', function(e) {
		var p = scale(e);
		var now = Date.now();
		var count = (now - lastClick.t < 400 && Math.abs(p.x - lastClick.x) < 30
			&& Math.abs(p.y - lastClick.y) < 30) ? 2 : 1;
		lastClick = { t: now, x: p.x, y: p.y };
		send('click', { x: p.x, y: p.y, count: count });
	}).on('dblclick', function(e) { e.preventDefault(); })
	 .on('contextmenu', function(e) {
		e.preventDefault();
		var p = scale(e);
		send('click', { x: p.x, y: p.y, button: 'right' });
	}).on('wheel', function(e) {
		e.preventDefault();
		send('scroll', { dy: e.originalEvent.deltaY });
	});
	$stage.on('keydown', function(e) {
		if (e.key.length === 1) send('type', { text: e.key });
		else if (['Enter','Backspace','Tab','Escape','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Delete','Home','End','PageUp','PageDown'].includes(e.key)) {
			send('key', { key: e.key });
		}
	});

	setInterval(function() {
		frappe.call({
			method: 'jgb.browser_stream.frame',
			callback: function(r) {
				var d = r.message;
				if (!d) return;
				if (d.alive) {
					$status.text(d.title ? d.title + ' — ' + d.url : 'streaming').css('color', '#8d99a6');
					if (d.ts !== lastTs && d.image) {
						lastTs = d.ts;
						$img.attr('src', 'data:image/jpeg;base64,' + d.image);
					}
				} else {
					$status.text('stream offline — is the browser-stream service running?').css('color', '#e74c3c');
				}
			}
		});
	}, 600);
};
