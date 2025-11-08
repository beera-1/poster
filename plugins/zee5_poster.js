import express from "express";
import fetch from "node-fetch";

const app = express();

app.get("/", async (req, res) => {
  try {
    const url = req.query.url;
    if (!url) return res.json({ ok: false, error: "Missing ?url parameter" });

    // 🔐 Zee5 accessToken (copy your valid one)
    const token =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwbGF0Zm9ybV9jb2RlIjoiV2ViQCQhdDM4NzEyIiwiaXNzdWVkQXQiOiIyMDI1LTExLTA3VDE5OjQ4OjIxLjAwMFoiLCJwcm9kdWN0X2NvZGUiOiJ6ZWU1QDk3NSIsInR0bCI6ODY0MDAwMDAsImlhdCI6MTc2MjU0NDkwMX0.a8bxsetMCTduyAaCyGEhUb7TuP9m1wc9eKmJRqmngJQ";

    const cookies =
      "isUserActive=yes; user-type=register; userTypeLaunchApi=REG; zutype=register; xaccesstoken=" +
      token;

    // 🌐 Fetch ZEE5 HTML page
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
    if (!matchJson)
      return res.json({ ok: false, error: "❌ No __NEXT_DATA__ found in HTML" });

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

    const posters = {
      list: find("1920x1080list")
        ? `${cdn}/list/${find("1920x1080list").split("/").pop()}`
        : null,
      portrait: find("720x1080withlogo")
        ? `${cdn}/portrait/${find("720x1080withlogo").split("/").pop()}`
        : null,
      cover: find("1920x770")
        ? `${cdn}/cover/${find("1920x770").split("/").pop()}`
        : null,
      app_cover: find("1920x1080appcover")
        ? `${cdn}/app_cover/${find("1920x1080appcover").split("/").pop()}`
        : null,
      logo: find("4320x2750")
        ? `${cdn}/title_logo/${find("4320x2750").split("/").pop()}`
        : null,
    };

    res.json({
      ok: true,
      resource_id: resourceId,
      posters,
    });
  } catch (err) {
    res.json({ ok: false, error: "⚠️ " + err.message });
  }
});

app.listen(8080, () => console.log("✅ Zee5 Poster API running on port 8080"));
