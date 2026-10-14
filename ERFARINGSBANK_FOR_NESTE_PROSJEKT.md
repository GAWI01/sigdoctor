# Erfaringsbank for neste prosjekt

**Grunnlag:** praktisk audit av Football Fantasy AI / FPL-AI, 11. oktober 2026, commit `5306fdcface2cfee01a177991369a564e4d213ab`, samt en supplerende kildekontroll av juridisk dokumentasjon og logging. Repository: https://github.com/GAWI01/fantasy-football-ai.

**Formål:** bruke erfaringene til å bygge neste produkt med færre feil. Dokumentet kan deles med Codex og Claude Code. Det er ikke en ordre om å implementere alt, og det er ikke en ny full juridisk eller sikkerhetsmessig gjennomgang.

Status brukes slik: **VERIFIED** = konkret kontrollert; **BROKEN** = feil gjenskapt; **NOT VERIFIED** = ikke avklart; **BLOCKED** = testen ble hindret. Juridiske spørsmål nedenfor er avklaringspunkter, ikke konklusjoner om lovbrudd. Gjeldende vilkår og regler må undersøkes for landet, datakilden og produktet som faktisk skal lanseres.

## 1. Det viktigste vi lærte

En grønn testpakke og en pen frontend er ikke nok til å vise at produktet hjelper brukeren. I FPL-AI bestod 476 Python-tester og 106 frontend-tester, og build/lint/typecheck gikk gjennom. Likevel fant auditen 28 dokumenterte problemer, hvorav ni med HIGH alvorlighetsgrad. Flere kom først frem ved å følge en hel brukerreise eller prøve kontrollerte, realistiske beslutningsscenarioer.

Behold det som virker. Next.js, FastAPI, den eksisterende optimizer-strukturen og publiserte modellfiler var ikke i seg selv problemet. De største feilene lå i beslutningsmålet, tidskonteksten, kontraktene mellom lag og håndteringen av ukjente data.

## 2. Konkrete feil og hvordan vi unngår dem neste gang

| Erfaring fra FPL-AI | Regel for neste prosjekt | Kontroll som bør finnes |
|---|---|---|
| **BROKEN:** reservekeeper ble prioritert selv om beste startende lag fikk null gevinst. ISSUE-002. | Optimaliser brukerens faktiske resultat, ikke et lett tilgjengelig surrogatmål. | En kandidat som bare forbedrer en irrelevant sum skal tape mot en kandidat som forbedrer resultatet. |
| **BROKEN:** optimizer valgte transfer A, forklaringen valgte B, mens resultatlaget fortsatt beskrev A. ISSUE-003. | Ett valgt scenario må eie handling, tall, forklaring og resultattilstand. | Rekonstruer alle viste tall fra samme valgte scenario; sammenlign API og UI. |
| **BROKEN:** chips kunne anbefales med null beregnet verdi. ISSUE-004/025. | En anbefaling må slå alternativet «gjør ingenting», med samme beregningsregler. | Identisk tilstand skal ha null gevinst. Gratis endringer skal ikke krediteres en kostbar handling. |
| **BROKEN:** neste-GW-plan var utilgjengelig i en vanlig live-GW-fase. ISSUE-001. | Test produktets hovedløfte i hele livssyklusen, også mellom publiseringer. | Før frist, under kamp, etter kamp og før neste publisering; vis ærlig foreløpig modus der den finnes. |
| **BROKEN:** ulike TTL-er kunne blande picks fra én GW og tall fra en annen. ISSUE-008. | Freshness og snapshot-konsistens er forskjellige krav. | Samme event/version i alle deler av en sammensatt response. |
| **BROKEN:** manglende forecast eller historikk kunne tolkes som null eller en kjent verdi. ISSUE-013/024/026. | Skill ukjent, manglende, utdatert og bekreftet null. | Missing-input-test skal ikke skape en sikker anbefaling eller oppdiktet brukerstatus. |
| **BROKEN:** en blank runde kunne gjøre fremtidige runder feilaktig poengløse. ISSUE-006. | En midlertidig tilstand må ikke bli en permanent egenskap. | Blank nå og kamp senere; skade nå og usikker fremtid; riktig scope for hvert signal. |
| **BROKEN:** senere next-round skadestatus endret Live sin publiserte forventning, mens Review beholdt originalen. ISSUE-028. | Skill historiske forventninger fra reviderte fremtidsvurderinger. | Senere nyheter må ikke omskrive en frosset prognose som brukes til evaluering. |
| **BROKEN:** ugyldig Team ID gav ustrukturert 500 og dårlig nettleserfeil. ISSUE-007. | Feil må ha en kontrakt hele veien til brukerens neste handling. | Ikke funnet, timeout, backend nede, retry og siste gode data. |
| **BROKEN:** ufullført solver-søk kunne bli forklart som sikker HOLD. ISSUE-009. | «Beste funnet» er ikke det samme som «bevist best». | Status, søkeomfang og optimalitet må være synlige i API og forklaring. |
| **BROKEN:** gjentatte samtidige requests brukte opp upstream-kvoten. ISSUE-012. | Del pågående kall til samme ressurs; sett grenser og timeouts. | Deterministisk cold-cache concurrency-test med kontrollert upstream. |
| **BROKEN:** research-sider beholdt gamle data uten å vise refresh-feil. ISSUE-018. | Siste gode data kan beholdes, men alder og feil må fortsatt vises. | Last lykkes → neste refresh feiler → gamle data + warning + retry. |
| **BROKEN:** tablet-navigasjon, blokkert storage og URL-filtre hadde egne feil. ISSUE-022/023/027. | Test reell interaksjon og tilstand, ikke bare screenshots ved to bredder. | Mobil, mellomstor skjerm, desktop, keyboard, reload/back og storage-feil. |

Andre domener har tilsvarende problemer: et budsjettverktøy kan optimalisere omsetning fremfor fortjeneste, en bookingapp kan blande lagerstatus fra ulike tidspunkt, og en AI-assistent kan forklare et annet svar enn det systemet faktisk valgte.

## 3. Arbeidsmåte før du bygger mye

1. **Skriv ned beslutningen produktet skal forbedre.** Hvem er brukeren, hva gjør de i dag, og hvilken konkret handling skal bli enklere eller bedre?
2. **Avklar datakilder og rettigheter tidlig.** Et produkt som avhenger av en kilde du ikke kan bruke på ønsket måte, har en grunnleggende begrensning.
3. **Bygg én komplett brukerreise først.** Input → hent/valider data → beregn → forklar → brukerens handling → recovery ved feil. Deretter utvides funksjonene.
4. **Definer kontrakter og invarianter.** Enheter, tidsperioder, provenance, unknown-status, gyldige tilstander og hvem som eier sannheten.
5. **Lag en enkel baseline.** En mer avansert modell eller agent må vise nytte mot et enklere alternativ.
6. **Test driftsovergangene.** Utdaterte data, ny periode, deploy med gammel klient, upstream-endring og avbrutt beregning.

Unngå å bygge mange dashboardkort før den sentrale handlingen fungerer. En funksjon bør ha et tydelig svar på: «Hvilken beslutning blir bedre av dette?»

## 4. Data, AI og modeller

- Merk kilden: offisiell verdi, modellverdi, heuristikk eller brukerens simulering. Disse kan vises sammen, men må ikke behandles som samme sannhet.
- Lagre enheter eksplisitt. Pris i tideler, kroner/pund, next-period points, vektet horisont og netto etter kostnad må ikke blandes.
- Bevar datakontrakter ved modellendringer. Å rette en feildefinert feature kan kreve retrening og ny sertifisering, ikke bare en runtime-patch.
- Evaluer flere relevante mål. FPL-poengmodellen slo den testede enkle baselinen på samlet feil, mens xMinutes ikke viste samme forbedring. Én god metric beviser ikke at alle modellkomponenter er gode.
- Bruk bare informasjon som var tilgjengelig på beslutningstidspunktet ved historisk evaluering. Retrospektive kilder uten datert snapshot begrenser hva man kan bevise.
- Skill modellens rå output fra senere risikojusteringer. Flere multipliers kan telle samme skade-/fixture-/minuttrisiko flere ganger.
- «HIGH confidence» må ha en forklaring og evaluering. En heuristisk score er ikke automatisk en sannsynlighet.
- Arkiver publiserte prognoser og inputs med tidspunkt, versjon og hashes. En hash dokumenterer identitet, ikke lovlig bruk eller modellkvalitet.
- Pins modellmiljøet. Native API-serving og offline sklearn-replay har ulike behov; en modellfil er ikke garantert portabel til vilkårlige bibliotekversjoner.

Målet med AI-laget er å redusere brukerens research og prioritere en handling. En ekstra score eller generisk forklaring gir liten verdi hvis den ikke beskriver det valgte scenarioet og usikkerheten.

## 5. Testing som gir produktverdi

Prioriter disse lagene:

1. **Domeneinvarianter:** lovlige regler, budsjett, tidskontekst og identisk baseline.
2. **Kontrakttester:** faktiske upstream-shapes → normalisering → API → frontend.
3. **Scenarioer:** sterk tilstand som bør beholdes, svak tilstand, lite budsjett, flere handlinger og ufullstendige inputs.
4. **Feil/recovery:** timeout, ugyldig ID, stale cache, malformed respons og samtidige requests.
5. **Nettleserreise:** onboarding, import, analyse, simulering, refresh, endring av input og tilgjengelighet.
6. **Modellreplay:** reproduser output og sammenlign mot baseline med identisk evalueringsgrunnlag.

Test observerbar oppførsel, ikke bare at felt eller funksjoner finnes. En kontrollert probe som bekrefter en feil, må omskrives til en regression-test som forventer korrekt oppførsel når feilen rettes. Skill miljøfeil fra produktfeil: auditens Docker-build var BLOCKED av nettverk/CA, ikke bevist ødelagt av prosjektet.

## 6. Juridiske erfaringer og spørsmål før lansering

### Det prosjektet faktisk allerede har dokumentert

**VERIFIED:** `README.md`, `docs/DATA_SOURCES.md` og `docs/DATA_USE_RELEASE_GATE.md` beskriver datakilder, uavhengighet og en gratis, ikke-kommersiell produktgrense. Disclaimer finnes også i `frontend/components/shell/AppShell.tsx` og Settings.

Release-gaten beskriver offentlig gratis drift som en kjent risiko akseptert av eieren, og setter krav om skriftlig tillatelse eller egnet lisensiert kilde før kommersiell bruk. Dette er prosjektets dokumenterte vurdering. Den er ikke en uavhengig bekreftelse på at dagens upstream-vilkår tillater bruken. Auditen gjennomførte ikke en ny juridisk verifisering av vilkårene.

I undersøkt checkout ble ingen egen sporet LICENSE-fil funnet. Det ble heller ikke funnet egne personvern-/vilkårssider eller kontakt-/takedown-lenke i de undersøkte frontend-rutene. Dette beviser ikke at avtaler eller informasjon mangler andre steder; det viser hva neste agent eller prosjekteier bør avklare.

### Avklaringsliste for neste prosjekt

| Tema | Spørsmål som må besvares | Praktisk dokumentasjon |
|---|---|---|
| API, scraping og datarettigheter | Har vi rett til uthenting, cache, viderevisning, trening og ønsket gratis/kommersiell bruk? | Daterte vilkår, datakilderegister, lisens/tillatelse og begrensninger. «Offentlig tilgjengelig» er ikke i seg selv en gjenbrukslisens. |
| Kode- og datalisenser | Hvilke plikter følger av kode, datasett, modeller, fonter og bilder? | Lisens-/attributionsoversikt. Kodelisens avklarer ikke nødvendigvis rettighetene til underliggende data. Et offentlig repo uten lisens gir ikke automatisk fri gjenbruksrett. |
| Varemerker og opphavsrett | Kan navn, logoer, bilder og annet materiale brukes slik vi planlegger? | Egne assets eller dokumentert tillatelse; tydelig uavhengighet. En disclaimer erstatter ikke nødvendige rettigheter. |
| Personvern | Kan data identifisere en person, også gjennom ID-er eller kobling til andre data? | Dataflyt, formål, behandlingsgrunnlag der reglene gjelder, informasjon, lagringstid og håndtering av rettigheter. Offentlige personopplysninger er ikke automatisk unntatt. |
| Logger og leverandører | Hva mottar hosting, analyseverktøy, AI-leverandør og feilovervåking? | Dataminimering, loggretensjon, tilgang, leverandørroller/databehandleravtaler der relevant og vurdering av overføringer. Ikke anta at alt er lokalt. |
| Cookies og localStorage | Hva er nødvendig for ønsket funksjon, og hva brukes til analyse eller markedsføring? | Klassifiser formål og kontroller gjeldende samtykke-/informasjonskrav. Ikke anta at alt krever banner, eller at localStorage faller utenfor reglene. |
| Betaling og markedsføring | Hvilke regler gjelder hvis vi tar betalt eller lover en bestemt effekt? | Tydelige priser, abonnement/avbestilling, forbrukerrettigheter og dokumentasjon for påstander; avklar skatt/MVA ved behov. |
| AI-regler | Hvilke regler gjelder for denne bruken, rollen og jurisdiksjonen? | Vurder faktisk funksjon, brukere, risiko og gjeldende ikrafttredelse. «Bruker AI» er ikke alene en risikoklassifisering. |

Et nytt betalt produkt må vurderes på nytt selv om en gratis beta tidligere var akseptert internt. Ikke kontakt rettighetshavere, send brukerdata eller inngå avtaler automatisk; forbered underlaget og la prosjekteieren håndtere mandatet.

Start med primærkildene: dataleverandørens egne vilkår, [Datatilsynet](https://www.datatilsynet.no/), [Nkom](https://nkom.no/), [Forbrukertilsynet](https://www.forbrukertilsynet.no/) og offisielle lovtekster. Skaff konkret juridisk vurdering når rettighetsgrunnlaget eller lanseringsmodellen er uklart.

### En konkret personvern-/dokumentasjonslæring fra FPL-AI

**VERIFIED gjennom kildekontroll:** nettleseren lagrer Team ID lokalt, men ID-en sendes også til backend. `backend/observability.py:79/92` logger request-path, som kan inneholde ID-en, og `backend/fpl_gateway.py:109–157` cacher offentlige manager-responser i serverminne. Det er noe annet enn en permanent managerprofil.

**NOT VERIFIED:** faktisk loggretensjon, tilgang og behandling hos hosting-/driftsleverandørene. Det er ikke fastslått at denne behandlingen er ulovlig.

Læringen er å skrive presist: skill **lokal persistens**, **backend-behandling/cache** og **driftslogger**. Setningen «data lagres bare i nettleseren» kan beskrive for lite av den reelle dataflyten. Vurder maskering av manager-ID i logger dersom rå ID ikke trengs til drift.

En tilknyttet erfaring: «Disconnect» fjerner Team ID og FT-overstyring, men ikke lokal planhistorikk eller sesongmål (`frontend/app/providers/TeamProvider.tsx:127`). Det er ikke automatisk en feil ved frakobling. Neste produkt bør skille «koble fra», «tøm lokal historikk» og eventuell «slett serverdata», og teste at hver handling gjør det teksten lover. Cache-TTL for ferskhet er heller ikke automatisk en slettefrist.

## 7. Sikkerhet og drift før du deler produktet offentlig

Dette er generelle forhåndskontroller, ikke påstander om nye sikkerhetsfunn i FPL-AI:

- Ingen secrets i repo, frontend-bundle, screenshots eller feillogger. Skill offentlige config-verdier fra hemmelige nøkler.
- Valider input og avgrens eksterne fetch-mål. Vurder autentisering, tilgangskontroll og misbruksgrenser ut fra funksjonene som faktisk finnes.
- Ha eksplisitte timeouts, kostnadsgrenser og bounded retries for API-er og AI-kall.
- Bruk lockfiler og nødvendige versjonspins. Installer ikke tilfeldige avhengigheter for å løse et problem som kan håndteres enklere.
- Test et rent miljø og dokumenter hvilke nettverks-/CA-/credential-forutsetninger det krever.
- Ha kontaktpunkt, rollback og måte å stenge tjenesten på ved alvorlig feil eller rettighetskrav.
- Les deployment-oppsettet før merge/push. I dette repoet kan merge til `master` utløse produksjonsdeploy.

## 8. Samarbeid mellom coding-agenter

- Gi agentene samme mål, arkitekturgrenser, kontrakter og statusdefinisjoner.
- Fordel tydelige områder. Unngå samtidige endringer av samme kontrakt uten koordinering.
- Krev konkret reproduksjon før fix. Skill bug, svak modell, antakelse, produktvalg og miljøblokkering.
- Bevar brukerendringer og fungerende kode. Ikke omskriv systemet fordi en agent foretrekker en annen stil.
- Handoff skal oppgi commit, fil/funksjon, hva som faktisk ble kjørt, resultat og åpne spørsmål.
- Dokumentasjonen må oppdateres når implementasjonen endres; historiske testtall og arkitekturpåstander skal ikke fremstå som dagens status.

## 9. Kort sjekkliste for neste prosjekt

### Før bygging

- [ ] Én konkret brukerreise og beslutning er definert.
- [ ] Datakilder, lisens-/rettighetsgrunnlag og ønsket lanseringsmodell er kartlagt.
- [ ] Enheter, tidskontekst, provenance og unknown-status er definert.
- [ ] Enkel baseline og viktigste produktinvarianter er valgt.

### Før beta

- [ ] Hovedreisen fungerer med faktiske data, ikke bare mocks.
- [ ] Gjør-ingenting-alternativet og feilscenarioer er testet.
- [ ] Samme scenario og tilstand vises i hele produktet.
- [ ] Loading, stale, error, retry og refresh er forståelige.
- [ ] Mobil, tablet, desktop og keyboard er prøvd.
- [ ] Bygg/testmiljø og begrensninger er dokumentert.

### Før offentlig eller kommersiell lansering

- [ ] Rettigheter og produktpåstander er vurdert for faktisk bruk.
- [ ] Personverninformasjon samsvarer med hele dataflyten, inklusive logger og leverandører.
- [ ] Nødvendige lisens-/attributionskrav og eventuelle avtaler er håndtert.
- [ ] Drift, kostnadsgrenser, kontakt og rollback er på plass.
- [ ] Hele reisen er retestet på aktuell checkout; BLOCKED/NOT VERIFIED er ikke fremstilt som bestått.

## 10. Prompt du kan sende til Codex og Claude Code

Kopier teksten nedenfor til hver instans, gjerne sammen med denne filen:

> Gå gjennom arbeidet ditt med dette prosjektet og lag et erfaringsnotat for neste prosjekt. Ikke implementer endringer nå.
>
> Beskriv konkrete feil, hindringer og antakelser som faktisk viste seg feil. Ta med teknikk, data, AI/ML, brukerreise, testing, deploy, sikkerhet og rettighets-/personvernspørsmål der de er relevante. Ikke finn på problemer for å fylle kategoriene.
>
> For hvert punkt: observasjon, evidens/reproduksjon, årsak eller hva som fortsatt er ukjent, konsekvens, hva som ville forebygget det, og en konkret kontroll vi kan bruke neste gang. Oppgi commit og relevante filer når du kan.
>
> Bruk VERIFIED, BROKEN, NOT VERIFIED og BLOCKED. Skill eget observert problem fra generelt råd. Skill juridisk dokumentasjon fra verifisert tillatelse; ikke konkluder med lovbrudd uten grunnlag. Ta med hva som fungerte godt og bør beholdes.
>
> Avslutt med de fem viktigste lærdommene, en kort oppstarts-/lanseringssjekkliste og åpne spørsmål til prosjekteieren. Lever én Markdown-fil som kan leses uten resten av samtalen. Ikke push, deploy, kontakt tredjeparter eller endre produktet.

Når notatene kommer tilbake, slå sammen like punkter, behold kilde/commit og marker uenigheter. Gjør bare gjentakende eller alvorlige erfaringer til faste prosjektregler; ikke la enhver engangsfeil bli en ny prosess.

## 11. Mal for nye erfaringer

```text
ID / kort tittel:
Prosjekt / commit / dato:
Kategori: produkt | teknikk | data | modell | UX | drift | sikkerhet | juridisk
Status: VERIFIED | BROKEN | NOT VERIFIED | BLOCKED
Observasjon og evidens:
Årsak / usikkerhet:
Konsekvens for bruker eller prosjekt:
Forebygging neste gang:
Konkret test eller kontroll:
Hva som fungerte og bør beholdes:
Ansvarlig / åpent spørsmål:
```

**Referanse:** den detaljerte FPL-auditen heter `FOOTBALL_FANTASY_AI_PRACTICAL_PRODUCT_AUDIT.md`, og den konkrete fix-prompten heter `IMPLEMENTATION_PROMPT.md`. De gir detaljene bak issue-ID-ene. Denne erfaringsfilen kan brukes selvstendig.
