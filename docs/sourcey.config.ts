import { defineConfig, markdown } from "sourcey";

export default defineConfig({
  name: "Agentic Fabric",
  siteUrl: "https://agentic.coach",
  baseUrl: "/",
  ogImage: "./assets/agentic-fabric-hero.jpg",
  repo: "https://github.com/jbcom/agentic-fabric",
  editBranch: "main",
  prettyUrls: "slash",
  theme: {
    preset: "default",
    colors: {
      primary: "#2457a6",
      light: "#3974c9",
      dark: "#173b72",
    },
    fonts: {
      sans: "Inter",
      mono: "JetBrains Mono",
    },
  },
  navigation: {
    tabs: [
      {
        tab: "Documentation",
        slug: "",
        source: markdown({
          groups: [
            { group: "Start here", pages: ["index", "getting-started"] },
            {
              group: "Concepts",
              pages: ["architecture", "agentic-workflows", "protocols", "vendor-fabric", "pillars"],
            },
            { group: "Reference", pages: ["api-reference"] },
            { group: "Project", pages: ["development", "contributing", "changelog"] },
          ],
        }),
      },
    ],
  },
  navbar: {
    links: [{ type: "github", href: "https://github.com/jbcom/agentic-fabric" }],
  },
  footer: {
    links: [{ type: "github", href: "https://github.com/jbcom/agentic-fabric" }],
  },
});
