const url = "https://clck.mgid.com/ghits/26433993/i/57808524/0/src/950562051/pp/15/1";
const referer = "https://brainberries.co/";

async function test() {
  console.log("Testing resolution for:", url);
  try {
    const response = await fetch(url, {
      method: "GET",
      redirect: "follow",
      headers: {
        Referer: referer,
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
      },
    });
    console.log("Final URL:", response.url);
  } catch (e) {
    console.error("Error:", e);
  }
}

test();
