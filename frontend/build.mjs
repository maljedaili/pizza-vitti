import * as esbuild from "esbuild";

const watch = process.argv.includes("--watch");
const shared = {
  bundle: true,
  minify: !watch,
  sourcemap: watch,
  logLevel: "info",
};

const builds = [
  {
    ...shared,
    entryPoints: ["frontend/site.js"],
    outfile: "shop/static/shop/dist/site.js",
  },
  {
    ...shared,
    entryPoints: ["frontend/site.css"],
    outfile: "shop/static/shop/dist/site.css",
    external: ["/static/*"],
  },
];

if (watch) {
  const contexts = await Promise.all(builds.map((options) => esbuild.context(options)));
  await Promise.all(contexts.map((context) => context.watch()));
  console.log("Pizza Vitti frontend watch mode is running.");
} else {
  await Promise.all(builds.map((options) => esbuild.build(options)));
}
