<p align="center">
  <img src="BeefMC.png" alt="BeefMC" width="420">
</p>

# BeefMC

BeefMC currently targets Minecraft 1.8.8, 1.21.11, 26.1.2, and 26.3. Its 1.8.8 version is based on PandaSpigot; modern versions are based on Leaf, which is derived from Paper. BeefMC focuses on memory use, performance, and plugin compatibility.

## Performance and compatibility

Optimizations and measured results are recorded in the [performance record](PERFORMANCE.md). BeefMC makes no memory or performance claim without measurements from a documented workload. Build success alone does not prove runtime stability or plugin compatibility.

## Releases

GitHub releases use one `vMAJOR.MINOR.PATCH` tag and build a jar plus SHA-256 checksum for each supported version. `v0.0.0` is an initial pre-release; it does not claim production readiness or plugin compatibility.

## Contributing and building

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch, CI, and review guidance. Follow the build instructions and JDK requirements in the [version support guide](docs/architecture/version-support.md).

## License and attribution

BeefMC retains upstream licenses and copyright notices. Leaf is developed by [Winds Studio](https://github.com/Winds-Studio/Leaf), Paper by [PaperMC](https://github.com/PaperMC/Paper), and PandaSpigot by [hpfxd](https://github.com/hpfxd/PandaSpigot).
