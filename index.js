// index.js
import express from "express";
import fetch from "node-fetch";
import "./bot.js"; // your Telegram bot

const app = express();

// ZEE5 poster route
app.get("/", async (req, res) => {
  const url = req.query.url;
  if (!url) return res.json({ ok: false, error: "Missing ?url" });

  const token = "your_access_token_here";
  const cookies = "isUserActive=yes; user-type=register; xaccesstoken=" + token;

  const htmlRes = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Cookie: cookies,
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
      Accept: "text/html,application/xhtml+xml",
    },
  });

  const html = await htmlRes.text();
  const matchJson = html.match(
    /<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/
  );
  if (!matchJson) return res.json({ ok: false, error: "No NEXT_DATA" });

  const json = JSON.parse(matchJson[1]);
  const data =
    json?.props?.pageProps?.data || json?.props?.pageProps?.pageData || {};
  const all = JSON.stringify(data);

  const find = (pattern) =>
    (all.match(
      new RegExp(`(${pattern}[^"']+\\.(jpg|jpeg|png|webp|avif))`, "i")
    ) || [])[1];

  const resourceId = url.match(/([0-9]-[0-9]-1z[0-9]+)/i)[1];
  const cdn = `https://akamaividz2.zee5.com/image/upload/resources/${resourceId}`;

  res.json({
    ok: true,
    posters: {
      portrait: find("portrait")
        ? `${cdn}/portrait/${find("portrait").split("/").pop()}`
        : null,
      app_cover: find("app_cover")
        ? `${cdn}/app_cover/${find("app_cover").split("/").pop()}`
        : null,
      logo: find("title_logo")
        ? `${cdn}/title_logo/${find("title_logo").split("/").pop()}`
        : null,
    },
  });
});

// 🟢 Start Express server
app.listen(8080, () => console.log("✅ Bot + Zee5 Poster API running on port 8080"));
