import Head from "next/head";
import { FournisseurAuth } from "@/lib/auth";
import { FournisseurTheme } from "@/lib/theme";
import { FournisseurToast } from "@/components/ui";
import "@/styles/globals.css";

export default function App({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>SkillSeek AI</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <FournisseurTheme>
        <FournisseurAuth>
          <FournisseurToast>
            <Component {...pageProps} />
          </FournisseurToast>
        </FournisseurAuth>
      </FournisseurTheme>
    </>
  );
}
