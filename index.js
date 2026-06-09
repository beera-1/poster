const express = require("express");
const puppeteer = require("puppeteer");

const app = express();

app.get("/fetch", async (req, res) => {
    const targetUrl = req.query.url;

    if (!targetUrl) {
        return res.status(400).json({
            success: false,
            error: "Missing url parameter"
        });
    }

    let browser;

    try {
        browser = await puppeteer.launch({
            executablePath:
                process.env.PUPPETEER_EXECUTABLE_PATH ||
                "/usr/bin/chromium",
            headless: true,
            args: [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        });

        const page = await browser.newPage();

        await page.goto(targetUrl, {
            waitUntil: "networkidle2",
            timeout: 60000
        });

        const hubLink = await page.evaluate(() => {
            return new Promise((resolve) => {
                let count = 0;

                const timer = setInterval(() => {
                    const links = [...document.querySelectorAll("a")];

                    const found = links.find(
                        a => a.href && a.href.includes("hubcloud")
                    );

                    if (found) {
                        clearInterval(timer);
                        resolve(found.href);
                        return;
                    }

                    count++;

                    if (count >= 30) {
                        clearInterval(timer);
                        resolve(null);
                    }
                }, 1000);
            });
        });

        res.json({
            success: true,
            link: hubLink
        });

    } catch (err) {
        res.status(500).json({
            success: false,
            error: err.message
        });
    } finally {
        if (browser) {
            await browser.close().catch(() => {});
        }
    }
});

const PORT = 3000;

app.listen(PORT, "0.0.0.0", () => {
    console.log(`API running on ${PORT}`);
});
