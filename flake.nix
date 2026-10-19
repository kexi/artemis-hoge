{
  description = "Expo Android and Artemis test environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      treefmt-nix,
    }:
    let
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      eachSystem = nixpkgs.lib.genAttrs systems;
      pkgsFor = system: import nixpkgs { inherit system; };
      formatting =
        system:
        treefmt-nix.lib.evalModule (pkgsFor system) {
          projectRootFile = "flake.nix";
          programs.nixfmt.enable = true;
          programs.ruff-format.enable = true;
          programs.just.enable = true;
          programs.oxfmt.enable = true;
          settings.global.excludes = [
            "pnpm-lock.yaml"
            "uv.lock"
            "flake.lock"
          ];
        };
    in
    {
      formatter = eachSystem (system: (formatting system).config.build.wrapper);
      checks = eachSystem (system: {
        formatting = (formatting system).config.build.check self;
      });
      devShells = eachSystem (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              nodejs_24
              pnpm
              uv
              just
              lefthook
              gitleaks
              pinact
              actionlint
              ghq
              android-tools
              scrcpy
              ffmpeg
              jdk17
            ];
            shellHook = ''
              export JAVA_HOME=${pkgs.jdk17}
              if [ -d .git ]; then
                lefthook install
              fi
            '';
          };
        }
      );
    };
}
