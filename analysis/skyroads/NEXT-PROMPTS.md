# Modellval och nästa prompter

Latest 2026-10-10: [real-time response and original menus](RESPONSE-MENUS-CHECKPOINT.md).
Original main/Controls/Help/30-road menu frames now match; preview at
http://127.0.0.1:8766/menu-viewer.html . Gameplay integration and fades remain.
Real-time native287-step and browser230-step checks pass; physical response,
initial timer phase and catch-up input remain explicitly unproven.

Aktuell ordning enligt användarens förtydligande: först funktionell och spelmässig
likhet med originalet, därefter Rust för Windows/macOS/Linux och webbexport.
Tidigare delsteg nedan är historik; den aktuella fortsättningsprompten finns under
”Nästa steg: respons och återstående originalförlopp”.

Arbetsrekommendationer för SkyRoads, inte uppmätta modelljämförelser. Sol 6.1
High har klarat verktygsinstallationen, verifierad uppackning, LZS-avkodning
mot originalkod och banvisaren. Modellbyte behövs inte för fortsatt rutinjobb.

OpenAI Docs beskriver Sol 6.1 som nära Astra för komplext arbete till lägre
kostnad, och Astra som modellen för det mest krävande arbetet. Båda har
`high`, `xhigh` och `max`. Extra High avser här steget över High i din modellväljare;
kontrollera etiketten i appen. Större resonemangsbudget garanterar inte att en
hypotes blir korrekt; bytes, spårningar och jämförelser är fortsatt facit.

Källor:
- https://developers.openai.com/api/docs/models/gpt-6.1-sol
- https://developers.openai.com/api/docs/models/gpt-6-astra

## Sol 6.1 High — avgränsad implementation med tydligt facit

> Fortsätt med att kartlägga de återstående resurscontainrarna i SkyRoads och
> använd den verifierade LZS-avkodaren där formatet stämmer. Spara originalhash,
> avkodade bytes och en manifestfil. Lägg till förhandsvisningar där formatet är
> belagt, och redovisa osäkra tolkningar separat. Bevara originalfilerna.

Passar extraktion, verktyg, export, UI, dokumentation och rutinmässig felsökning.

## Sol 6.1 Extra High — tile- och kollisionssteget, nu klart

> Kartlägg SkyRoads tileformat och kollisionsregler. Börja med
> GetRoadTileAtPosition (1000:04c0), GetRoadSupportHeight (1000:0c26),
> FUN_1000_1631, FUN_1000_1732 och FUN_1000_0533. Härled strukturprofiler,
> höjdtabeller och relevanta bitfält från rå instruktioner. Verifiera utvalda
> fall med isolerad originalkod innan du ger rutorna namn. Uppdatera
> banvisaren med belagda mark- och strukturtyper, inklusive osäkerheter.

Passar ett sammanhängande subsystem med segmentregister, fixed-point-värden,
flera anropskonventioner och många gränsfall. Detta steg är nu klart: 41328 originalkodsjämförelser passerar. Nästa större
modellbygge är skeppsfysiken under Astra High-prompten nedan.

## Sol 6.1 Max — vid en envis, väl lokaliserad avvikelse

> Pythonmodellen och originalrutinen skiljer sig i bifogad verifieringsrapport.
> Lokalisera den första avvikande instruktionen och tillståndsövergången.
> Pröva tydliga hypoteser om 16-bitars overflow, signedness, flaggor,
> segmentalias, SS=DS och argumentkonventioner. Korrigera modellen eller
> testmiljön utifrån spårningen och kör den relevanta jämförelsen igen.
> Spara ett minimalt reproduktionsfall och belägg för orsaken.

Använd för ett konkret svårt fel som kvarstår efter vanlig spårning. Att ett
jobb har många filer är i sig inte skäl att välja Max.

## Astra High — flera subsystem måste bli en sammanhängande modell

> Återskapa SkyRoads skeppsfysik från RunGameplayLoop (1000:1fd9) och dess
> hjälprutiner. Förena position, styrning, hopp, kollisioner, markeffekter,
> tidssteg och resursförbrukning i en dokumenterad modell. Behåll originalets
> fixed-point-aritmetik och avrundning. Implementera en fristående simulator
> och jämför valda tillståndsövergångar med kontrollerad originalkod. Börja
> med verifieringskontraktet, spara evidens och markera kvarvarande oklarheter.

Passar när betydelsen av variabler och kod måste härledas över flera funktioner
och subsystem. Byt till Astra High före denna prompt om tid/budget tillåter.

Första delsteget är nu klart: rörelseresolvern och de två hopphjälparna matchar
originalkod i3,897 fall, inklusive mellanliggande spårningar. Fortsätt på High
med ett avgränsat verifieringskontrakt för en hel fysiktick:

> Läs analysis/skyroads/PHYSICS-CHECKPOINT.md och fortsätt med en verifierbar
> fysiktick från RunGameplayLoop. Återanvänd de redan verifierade rörelse- och
> hopprutinerna. Kartlägg även tillståndet som lever kvar i stacklokaler mellan
> tickar, bevara heltalsaritmetiken och spara checkpointen löpande.

Även fysikticken är nu klar:5,370 jämförelser mot originalkod passerar, inklusive
3,671 tickar med vidarefört tillstånd och alla25 krävda beteendegrenar.
Nästa konkreta prompt:

> Läs analysis/skyroads/PHYSICS-CHECKPOINT.md. Kartlägg den faktiska
> fysikfrekvensen i timerkoden och bygg därefter ett första styrbart visuellt test
> med den verifierade Pythonfysiken. Behåll deterministisk indata/replay och
> spara checkpointen. Återskapa inte redan verifierade subsystem från början.

## Astra Extra High eller Max — svår syntes eller granskning av likvärdighet

> Granska vår återimplementation mot originalbinären. Sök efter felaktiga
> antaganden i tillståndsmaskin, fixed-point-fysik, kollisioner och
> perspektivprojektion. Föreslå och kör särskiljande kontrollfall med originalet
> som facit, prioritera den första observerade beteendeskillnaden och laga
> orsaken. Redovisa exakt vilken likvärdighet som testats och vad som återstår.

Extra High först. Max när en central tvetydighet eller komplex avvikelse består
och extra analys är mer värdefull än snabb återkoppling. Jag rekommenderar ett
byte vid sådana övergångar; jag ändrar inte modellinställningen automatiskt.

## Historik: timer och styrbar prototyp klara

Timer/prototypsteget är nu genomfört med Sol6.1 Extra High:1324 timerfall och
2876 nya fysiksteg från prototypkörningar matchar originalkod. Den styrbara
webbvyn finns på http://127.0.0.1:8766/physics-viewer.html . Nästa prompt:

> Läs analysis/skyroads/PHYSICS-CHECKPOINT.md. Börja nästa grafiksteg med att
> kartlägga och extrahera SkyRoads originalresurser, inklusive paletter och
> skeppsgrafik där formatet kan beläggas. Återanvänd den verifierade
> LZS-avkodaren och spara manifest, bytes, förhandsvisningar och checkpoint.
> Behåll fysikprototypen och dess inspelningar som verifierad referens.

## Genomfört: första sammanhängande jämförelsen mot körande original

DOSBox-X kör nu hela originalprogrammet. Originalets positionsindexerade
`DEMO.REC` samt sju vanliga försök ger 4 667 jämförda fysiksteg; Python och JS
matchar vid de dokumenterade gränserna. Originalets vanliga bana klaras och
progression sparas i en separat kopia. Se `RUNNING-ORIGINAL.md`.

Det finns en mätt skillnad: klonen startar om direkt, medan originalets toningar
ger ungefär 2,2 sekunder till nästa försök. Fysikträffarna innebär därför inte
att hela spelupplevelsen redan är frame perfect.

## Genomfört: originalets grafik — 2026-10-10

Originalets VGA-perspektiv, färger/rutmönster, tunnelgeometri, skepp och skugga
används nu i spelvyn. 287 indexerade spelbilder matchar körande original; alla
30 banor plus demo, tio världar och åtta perspektivfaser är representerade.
Se `GRAPHICS-CHECKPOINT.md`. Fysik/inputkod är oförändrad och den nya körningens
328 steg matchar Python. Användaren har förtydligat att exakt omstartsväntetid
har lägre prioritet än traversalens känsla; toningarna ska fortfarande finnas.

## Genomfört: originalets musik och ljud — 2026-10-10

Tio AdLib-musikstycken och fem digitala effekter spelas nu i webbvyn.
21 552 registerskrivningar och 55 ljudanrop på fysiksteg matchar körande
original. Se `AUDIO-CHECKPOINT.md`. Fysik/input och inspelningsidentitet är
oförändrade; originalets P-paus behåller musiken och omstart laddar inte om den.

## Genomfört: dynamiska instrument — 2026-10-10

Hastighet, syre, bränsle, banförlopp, gravitation och hoppassistans använder
originalets maskgrafik och heltalsregler. 4 291 sammanhängande originalanrop,
554 pixeljämförda paneler och 467 isolerade originalkodfall passerar.
Se `HUD-CHECKPOINT.md`. Fysik/input/ljud och replayidentitet är oförändrade.

## Nästa steg: respons och återstående originalförlopp

> Fortsätt från analysis/skyroads/HUD-CHECKPOINT.md och CYCLE-CHECKPOINT.md.
> Prioritera originalets spelkänsla under traversal. Behåll de verifierade
> dynamiska instrumenten från originalkod och resurser. Behåll den verifierade
> ljudhändelsemodellen och originalets återvunna musik/effekter.
> Jämför input-till-bild-respons mot ett original som kör i realtid; skilj
> logisk frame-likhet från fysisk tangent-/skärmlatens. Utöka sammanhängande
> originalkörningar till frontalkrasch, resursbrist och sista banans avslut.
> Behåll verifierad heltalsfysik, originalets fasta perspektiv, inputkö och
> deterministisk replay. Originaltoningar och funktionell profilsparning kvarstår,
> men exakt omstartsväntetid har lägre prioritet. Spara evidens och checkpoint.
> Påbörja inte Rust-portningen ännu.

## Tidigare prompt: originalets övergångar och sparning

> Fortsätt från analysis/skyroads/CYCLE-CHECKPOINT.md och RUNNING-ORIGINAL.md.
> Återskapa originalets tonings- och meddelandefaser runt start, död/omstart,
> Escape och målgång, inklusive hur indata hanteras under övergångarna. Härled
> tiderna ur originalkod och körspår; hårdkoda inte den uppmätta omstartstiden.
> Implementera originalets initiala banprogression och funktionell sparning.
> Utöka jämförelsen till hela Game-händelse- och tidsförloppet med de sparade
> DOSBox-referenserna, och fyll kvarvarande luckor för frontalkrasch, slut på
> resurser och sista banan. Behåll verifierad heltalsfysik, deterministisk replay
> och versionshanterade inspelningsidentiteter. Modern rendering är tillåten.
> Spara evidens och checkpoint; påbörja inte Rust-portningen ännu.

## Tidigare prompt: etablera körande referens

> Fortsätt från analysis/skyroads/CYCLE-CHECKPOINT.md. Prioritera originalets
> spelbeteende före Rust-portning. Etablera en reproducerbar körande DOS-referens
> och jämför sammanhängande spelcykler på riktiga banor med samma indata, inklusive
> en lyckad banavslutning, död/omstart, paus, Escape/banval, resursförbrukning och
> progression. Lokalisera första skillnaden i tillstånd, händelser eller timing.
> Mät input- och bildrespons; granska kamera, animationer och ljudsignaler där de
> påverkar spelupplevelsen. Verifiera saknad funktionell meny/progress-sparning.
> Behåll verifierad heltalsfysik och deterministisk replay. Modern rendering är
> tillåten. Spara evidens, täckningsmatris, återstående avvikelser och checkpoint.

Rust är ett senare steg, efter spelmässig verifiering. Slutmålet är samma spel
byggbart och körbart på Windows, macOS och Linux samt enkelt exporterbart till web.
