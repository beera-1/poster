const express = require("express");
const puppeteer = require("puppeteer");

const app = express();

app.get("/", (req, res) => {
    res.send("Server is running");
});

app.get("/fetch", async (req, res) => {
    const targetUrl = req.query.url;

    if (!targetUrl) {
        return res.status(400).json({
            success: false,
            error: "Missing ?url="
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
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote",
                "--single-process"
            ]
        });

        const page = await browser.newPage();

        await page.goto(targetUrl, {
            waitUntil: "networkidle2",
            timeout: 60000
        });

        const hubLink = await page.evaluate(() => {
            return new Promise((resolve) => {
                let attempts = 0;

                const interval = setInterval(() => {
                    const links = [...document.querySelectorAll("a")];

                    const found = links.find(
                        a =>
                            a.href &&
                            (
                                a.href.includes("hubcloud") ||
                                a.href.includes("hubcloud.foo")
                            )
                    );

                    if (found) {
                        clearInterval(interval);
                        resolve(found.href);
                        return;
                    }

                    attempts++;

                    if (attempts >= 30) {
                        clearInterval(interval);
                        resolve(null);
                    }
                }, 1000);
            });
        });

        if (!hubLink) {
            return res.status(404).json({
                success: false,
                message: "HubCloud link not found"
            });
        }

        return res.json({
            success: true,
            link: hubLink
        });

    } catch (err) {
        console.error(err);

        return res.status(500).json({
            success: false,
            error: err.message
        });
    } finally {
        if (browser) {
            await browser.close().catch(() => {});
        }
    }
});

const PORT = process.env.PORT || 8000;

app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on port ${PORT}`);
});
