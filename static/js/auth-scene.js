// Pointer parallax for the login/register seed-packet scene.
// The scene is a real 3D solid, so the tilt is eased toward its target rather
// than snapped: a hard jump reads as a flat card being dragged.
(function () {
  var scene = document.getElementById("sv-scene");
  var tilt = document.getElementById("sv-tilt");

  if (!scene || !tilt) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var REST_RX = -9;
  var REST_RY = -21;
  var target = { rx: REST_RX, ry: REST_RY };
  var current = { rx: REST_RX, ry: REST_RY };
  var frame = null;

  function apply() {
    tilt.style.setProperty("--sv-rx", current.rx.toFixed(2) + "deg");
    tilt.style.setProperty("--sv-ry", current.ry.toFixed(2) + "deg");

    if (Math.abs(target.rx - current.rx) < 0.05 &&
        Math.abs(target.ry - current.ry) < 0.05) {
      frame = null;
      return;
    }
    current.rx += (target.rx - current.rx) * 0.18;
    current.ry += (target.ry - current.ry) * 0.18;
    frame = window.requestAnimationFrame(apply);
  }

  function steer(px, py) {
    target.ry = REST_RY - px * 14;
    target.rx = REST_RX + py * 8;
    if (frame === null) frame = window.requestAnimationFrame(apply);
  }

  scene.addEventListener("pointermove", function (event) {
    var box = scene.getBoundingClientRect();
    steer((event.clientX - box.left) / box.width - 0.5,
          (event.clientY - box.top) / box.height - 0.5);
  });

  scene.addEventListener("pointerleave", function () {
    steer(0, 0);
  });
})();
