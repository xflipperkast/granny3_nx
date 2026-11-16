# Switch EGL surface backend

`bash tools/mesa/build_switch.sh` builds the complete Switch Mesa graphics
libraries with `-Oz` and LTO. `build.sh` invokes it automatically. The SDK
installation stays intact: the runtime links the private EGL, GLESv2 and GL
dispatch archives in `.cache/mesa-switch/lib/` before the portlib directory.
Changes to these archives trigger relinking.

The source is [devkitPro Mesa](https://github.com/devkitPro/mesa/tree/05fc4b1d449b8fe12cf1a47b46c4a1c1f4e4e3a6),
whose Switch driver matches the `switch-mesa 20.1.0-5` package.
The source archive is checked against its pinned SHA-256 hash. All Mesa objects
are rebuilt together against the current SDK headers, preserving their shared
structure layouts. OpenGL, GLES 1 and GLES 2/3 remain enabled. Python generator
updates preserve XML iteration on current Python; the SDK supplies C11 time
functions. First builds need Meson, Ninja, Bison, Flex, m4 and Python Mako/PLY.
Compilation uses a temporary Linux directory to avoid Windows mount overhead.

The driver adds the following real capabilities:

- Enumerate multisample configs only when Gallium supports both the color
  format and the selected depth/stencil format at that sample count. Existing
  single-sample configurations keep their order and IDs.
- Allocate multisample color and depth/stencil storage for a window. Resolve
  its color into the single-sample native presentation buffer after pending GL
  vertices reach Gallium and before the frame is submitted. The presentation
  fence belongs to the resolved native buffer.
- Allocate independent pbuffer render targets, including matching multisample
  depth/stencil attachments. Pbuffers use single-buffer visuals, do not own an
  NWindow and do not count as display presents. The frontend uses native
  pbuffers whenever the host config advertises support.
- Forward EGL's requested share context to Gallium, so worker contexts can
  share their resources. Allocation failures release partial allocations and
  references; window cleanup cancels an outstanding dequeued buffer.

The installed Mesa archive and current newlib can have different C11 mutex
layouts. Rebuilding the entire stack keeps its private structures consistent;
the old hybrid-driver layout assertions apply only when explicitly building
against the installed archive's layout.

Contracts: [EGL config matching and sample attributes](https://registry.khronos.org/EGL/sdk/docs/man/html/eglChooseConfig.xhtml),
[pbuffer creation](https://registry.khronos.org/EGL/sdk/docs/man/html/eglCreatePbufferSurface.xhtml),
[swap semantics](https://registry.khronos.org/EGL/sdk/docs/man/html/eglSwapBuffers.xhtml).
Gallium's format checks, resources, blit interface and the state tracker's
pre-flush callback are implemented by the pinned Mesa source.

Switch GPU rendering and gameplay still require hardware verification.
Preserved-swap support, pixmaps, pbuffer texture
binding and native-window resizing remain unavailable in this backend.
Portrait presentation still uses GRNYX's existing single-sample offscreen
compositor; multisampling of that guest framebuffer remains a separate gap.
