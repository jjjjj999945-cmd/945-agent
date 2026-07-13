import { screens } from "./screens";

export function extractBody(source: string, folder: string) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(source, "text/html");
  const body = doc.body;
  const styleText = [...doc.querySelectorAll("style")]
    .map((style) => style.textContent ?? "")
    .filter(Boolean)
    .join("\n");

  body.querySelectorAll("script, link[rel='stylesheet']").forEach((node) => node.remove());
  body.querySelectorAll("[src]").forEach((node) => {
    const element = node as HTMLElement;
    const src = element.getAttribute("src");
    if (src?.startsWith("https://lh3.googleusercontent.com")) {
      const local = localAssetFor(src, folder);
      if (local) element.setAttribute("src", local);
    }
  });

  return {
    bodyClass: body.className,
    html: `${styleText ? `<style>${styleText}</style>` : ""}${body.innerHTML}`
  };
}

function localAssetFor(url: string, folder: string) {
  const screen = screens.find((item) => item.folder === folder);
  const asset = screen?.assets.find((item) => item.url === url);
  return asset ? `/stitch-reference/${folder}/${asset.file}` : undefined;
}
