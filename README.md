<p align="center">
  <img src="BeefMC.png" alt="BeefMC" width="420">
</p>

# BeefMC

BeefMC currently targets Minecraft 1.8.8, 1.21.11, 26.1.2, and 26.3. Its 1.8.8 version is based on PandaSpigot; modern versions are based on Leaf, which is derived from Paper. BeefMC focuses on memory use, performance, and plugin compatibility.

## Performance and compatibility

BeefMC v0.0.3 removes per-update waypoint connection snapshots on Minecraft 1.21.11, 26.1.2, and 26.3. In three paired 100-bot tests on 1.21.11, mean MSPT was 6.2% lower than BeefMC v0.0.2, with every pair improving. CPU results were mixed; these runs did not establish a RAM reduction. Minecraft 1.8.8 has no matching code path and is unchanged.

In a separate three-pair test against Paper 1.21.11 build 132 with 50 bots, BeefMC v0.0.3 averaged 11.1% lower per-run median CPU use and 22.8% lower sampled MSPT. Working set was 2.0% higher and private bytes 2.1% higher, so no RAM saving was measured. This synthetic test covers 1.21.11 only. Methods, run details, and limits are in the [performance record](PERFORMANCE.md).

Plugin, proxy, and production-network compatibility have not been validated. Build success alone does not establish runtime stability or compatibility.

## Releases

Latest release: [BeefMC v0.0.3](https://github.com/Sawlyer/BeefMC/releases/tag/v0.0.3). Each release builds one server JAR and SHA-256 checksum for Minecraft 1.8.8, 1.21.11, 26.1.2, and 26.3.

## Contributing and building

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch, CI, and review guidance. Follow the build instructions and JDK requirements in the [version support guide](docs/architecture/version-support.md).

## License and attribution

BeefMC retains upstream licenses and copyright notices. Leaf is developed by [Winds Studio](https://github.com/Winds-Studio/Leaf), Paper by [PaperMC](https://github.com/PaperMC/Paper), and PandaSpigot by [hpfxd](https://github.com/hpfxd/PandaSpigot).
