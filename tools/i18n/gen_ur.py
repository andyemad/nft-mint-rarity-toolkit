#!/usr/bin/env python3
"""Generate Roman Urdu (ur-Latn) translations of the NFT toolkit page.

TEXT / ATTR are in the exact order of strings.json, so the output keys are the
untouched English source strings. HEAD and JS are keyed by their source keys.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "strings.json")
OUT = os.path.join(HERE, "ur.json")

# --------------------------------------------------------------------------
# text: one value per entry of strings.json["strings"], same order
# --------------------------------------------------------------------------
TEXT = [
    "NFT toolkit | Aap ka onchain agent, Discord mein",  # 1
    "Setup guide par jayein",  # 2
    "NFT toolkit",  # 3
    "Apna khud ka agent",  # 4
    "Guide",  # 5
    "Skills",  # 6
    "Kharchay",  # 7
    "Vibe coding",  # 8
    "GitHub",  # 9
    "Free tools. Chalane ke liye aap ke.",  # 10
    "Onchain skills.",  # 11
    "Aap ke Discord mein.",  # 12
    "Ek simple message ko mint research, rarity rankings aur wallet intel mein badlein. Apna Hermes agent setup karein, phir kaam us se karwayein.",  # 13
    "Apna agent banayein",  # 14
    "31 skills dekhein",  # 15
    "Taqreeban 20 minute",  # 16
    "Windows, Mac aur Linux",  # 17
    "Aap ka Discord, upgrade",  # 18
    "Misaal",  # 19
    "your-onchain-agent",  # 20
    "Bas poochein. Kaam shuru.",  # 21
    "Y",  # 22
    "Aap",  # 23
    "Aaj 10:42",  # 24
    "@hermes",  # 25
    "is collection ko rank karein aur rare wale dikhayein",  # 26
    "Hermes",  # 27
    "APP",  # 28
    "Collection rank ho gayi. Ye teen sab se rare hain.",  # 29
    "Rarity report",  # 30
    "Demo collection",  # 31
    "Rank 1",  # 32
    "Rank 2",  # 33
    "Rank 3",  # 34
    "Sirf research. Koi transaction nahi bheji gayi.",  # 35
    "Ek message. Poori nayi skills.",  # 36
    "31 skills, kaam ke liye tayyar",  # 37
    "Research. Rank. Mint. Monitor.",  # 38
    "Rarity rankings",  # 39
    "Mint checks",  # 40
    "Wallet intel",  # 41
    "Aap ke agent ke peeche ke tools",  # 42
    "Discord",  # 43
    "OpenCode",  # 44
    "Open source. Toolkit ki koi subscription nahi.",  # 45
    "Ise dimagh dein",  # 46
    "Hermes install karein aur ek model connect karein.",  # 47
    "Ise Discord par le jayein",  # 48
    "Aap ka agent, bas ek message door.",  # 49
    "Skills ko kaam par lagayein",  # 50
    "Toolkit install karein. Jo chahiye poochein.",  # 51
    "Is guide mein",  # 52
    "Chalana shuru karein",  # 53
    "Aap ko kya chahiye",  # 54
    "Hermes setup karein",  # 55
    "Discord connect karein",  # 56
    "Skills install karein",  # 57
    "Ise kaam ka banayein",  # 58
    "Skill library",  # 59
    "Hashcats mint karein",  # 60
    "Kya kya pooch sakte hain",  # 61
    "Thora aage jayein",  # 62
    "Vercel se publish karein",  # 63
    "Kahan chalayein",  # 64
    "Kharcha kitna hai",  # 65
    "Troubleshooting",  # 66
    "Aap ke setup ki progress",  # 67
    "4 mein se 0",  # 68
    "Is browser mein save hai",  # 69
    "Thora setup. Phir bas chat.",  # 70
    "Yahan se shuru karein. Jo chahiye, usi order mein.",  # 71
    "~20 min setup",  # 72
    "Ho gaya",  # 73
    "Aap ko chahiye",  # 74
    "Kharcha",  # 75
    "Kis kaam ke liye",  # 76
    "Ek computer",  # 77
    "Free",  # 78
    "Agent chalata hai. Windows, Mac ya Linux, pichle kuch saal ka koi bhi",  # 79
    "Ek Discord account",  # 80
    "Agent se baat karne ka tareeqa, phone ya desktop se",  # 81
    "Ek OpenCode subscription",  # 82
    "~$10/month",  # 83
    "Agent ka dimagh. Sirf isi cheez ke paise dene hote hain",  # 84
    "Ek Vercel account",  # 85
    "(optional)",  # 86
    "Sirf agar aap koi page ya choti site online dalna chahte hain",  # 87
    "Ek chhota server",  # 88
    "~$5/month",  # 89
    "Sirf agar aap chahte hain ke computer band ho to bhi agent chalta rahe",  # 90
    "Ek Nous Portal account",  # 91
    "Portal par pricing dekhein",  # 92
    "Nous aap ke liye agent host kar sakta hai, to server ko haath lagane ki zarurat nahi",  # 93
    "Pehle teen se shuru karein. Vercel aur server baad mein aate hain aur aap dono mein se koi bhi\n    skip kar sakte hain.",  # 94
    "Hermes hi agent hai. Aap terminal window mein ek line paste karte hain aur ye khud install ho\n    jata hai. Is poori guide mein sab se technical cheez yahi hai.",  # 95
    "Windows",  # 96
    "Mac",  # 97
    "Linux",  # 98
    "Start menu kholein, likhein",  # 99
    "PowerShell",  # 100
    ", ise kholein aur ye paste karein:",  # 101
    "Dabayein",  # 102
    "Command + Space",  # 103
    ", likhein",  # 104
    "Terminal",  # 105
    ", Enter dabayein aur paste karein:",  # 106
    "Apna terminal kholein aur paste karein:",  # 107
    "Ye jo bhi chahiye khud download kar leta hai aur kuch minute leta hai. Text ko guzarne dein,\n    ise parhne ki zarurat nahi.",  # 108
    "Check karein ke ho gaya",  # 109
    "Window band karein, nayi kholein aur likhein:",  # 110
    "Ye ek checklist dikhata hai. Green ka matlab theek hai. Agar kuch missing ho to ye batata hai\n    ke usay theek karne wali exact command kya hai.",  # 111
    "Agent ko sochne ke liye ek model chahiye, aur wohi $10 wali subscription hai. Yahan sign up\n    karein:",  # 112
    "opencode.ai",  # 113
    "Phir jo key ye deta hai usay settings file mein add karein.",  # 114
    "Neeche ye line add karein, aur iski jagah",  # 115
    "apni key daalein,\n    phir save kar ke band karein:",  # 116
    "Mac aur Linux",  # 117
    "Ab ise batayein ke subscription use kare aur hello kahein:",  # 118
    "Agar jawab de de to agent chal raha hai. Is ke baad sab kuch usme cheezein add karna hai.",  # 119
    "Discord setup karein",  # 120
    "Yahi woh hissa hai jo ise kaam ka banata hai. Is ke baad terminal ki zarurat kabhi nahi\n    padegi. Aap sirf message karte hain.",  # 121
    "Discord apne menus waqt waqt par badalta hai, to agar koi button hil gaya ho to sab se milta\n    julta dhoondein.",  # 122
    "Yahan jayein",  # 123
    "discord.com/developers/applications",  # 124
    "aur click karein",  # 125
    "New\n      Application",  # 126
    ". Koi bhi naam dein.",  # 127
    "Bayein menu mein click karein",  # 128
    "Bot",  # 129
    ". Neeche scroll karein",  # 130
    "Privileged Gateway\n      Intents",  # 131
    "aur on karein",  # 132
    "Message Content Intent",  # 133
    "ko",  # 134
    "ON",  # 135
    ". Ye sab se zaroori hai: ise skip kiya to aap ka bot bilkul toota\n      hua lagega.",  # 136
    "Usi page par rehte hue click karein",  # 137
    "Reset Token",  # 138
    "aur jo aaye usay copy karein. Ye sirf ek baar dikhta\n      hai. Isay password ki tarah rakhein.",  # 139
    "Installation",  # 140
    ". On karein",  # 141
    "Guild Install",  # 142
    ", aur\n      check karein ke scopes mein ye shamil hain",  # 143
    "bot",  # 144
    "aur",  # 145
    "applications.commands",  # 146
    ". Jo install link ye dikhata hai\n      usay copy karein.",  # 147
    "Us link ko browser mein kholein aur bot ko apne server mein add karein. Us server ke aap owner\n      ya manager hone chahiye.",  # 148
    "Apni user ID dhoondein. Discord mein jayein",  # 149
    "Settings → Advanced",  # 150
    ", on karein",  # 151
    "Developer Mode",  # 152
    ", phir apne naam par right-click karein aur chunein",  # 153
    "Copy User\n      ID",  # 154
    ". Ye ek lamba number hai.",  # 155
    "Setup chalayein aur token aur user ID paste karein:",  # 156
    "Jab poochhe to Discord chunein. Phir ise start karein aur test karein:",  # 157
    "Woh window khuli chhoriye aur Discord mein bot ko direct message bhejein. Ise jawab dena\n    chahiye. Jab de de to dabayein",  # 158
    "Ctrl + C",  # 159
    "ise rokne ke liye, aur ye do lines chalayein taake is ke\n    baad ye khud start ho:",  # 160
    "Direct messages mein",  # 161
    "ye har cheez ka jawab deta hai.",  # 162
    "Server channel mein",  # 163
    "ye\n    sirf tab jawab deta hai jab aap @mention karein, to aap ke friends ko spam nahi hoga.",  # 164
    "Agar ye kabhi jawab na de",  # 165
    ", to taqreeban hamesha do mein se ek baat hoti hai: Message\n    Content Intent abhi bhi off hai, ya user ID ghalat copy hui. Steps 2 aur 6 dobara karein.",  # 166
    "Skills download karein",  # 167
    "Teen lines. Ye skills download karta hai aur aap ke agent mein install karta hai:",  # 168
    "Kabhi bhi check karne ke liye",  # 169
    ". Installer dobara\n    chalana safe hai, kuch nahi tootega.",  # 170
    "Git install nahi hai, ya pata nahi?",  # 171
    "ZIP yahan se download karein",  # 172
    "ye link",  # 173
    ",\n    ise unzip karein, us folder mein terminal kholein aur chalayein",  # 174
    "Aakhri baat, teen chhote helpers jo wallet aur trading skills ko chahiye:",  # 175
    "Onchain skill library",  # 176
    "Inhein yaad karne ki zarurat nahi. Agent khud sahi wala chun leta hai. Ye sirf is liye hai\n    ke aap ko pata ho aap kya maang sakte hain.",  # 177
    "31 skills search karein",  # 178
    "Sab skills",  # 179
    "Minting",  # 180
    "Rarity",  # 181
    "Verification",  # 182
    "Wallets",  # 183
    "Create",  # 184
    "Research aur tools",  # 185
    "31 skills kaam par lagane ke liye",  # 186
    "nft-mint-recon",  # 187
    "Pata karta hai ke mint asal mein kya hai",  # 188
    "Asal contract, asal price, mint waqai khula hai ya nahi, aur kis network par hai — sab dhoondta hai. Yahi woh skill hai jo fake price se thagi se bachati hai.",  # 189
    "Playbook dekhein",  # 190
    "nft-mint-recon ke liye",  # 191
    "seadrop-rapid-mint",  # 192
    "Kai wallets se ek saath mint karta hai",  # 193
    "Un drops ke liye jo seconds mein bik jate hain. Wallets banata hai, batata hai ke har ek mein kitna dalna hai, aur mint khulte hi fire kar deta hai.",  # 194
    "seadrop-rapid-mint ke liye",  # 195
    "nft-floor-sweep",  # 196
    "Poora floor kharidne ka hisaab lagata hai",  # 197
    "Collection ki har sasti listing ka hisaab jorta hai aur sab kharidne se pehle asal total batata hai.",  # 198
    "nft-floor-sweep ke liye",  # 199
    "onchain-claim-reverse-engineering",  # 200
    "Claim kaise karna hai ye nikalta hai",  # 201
    "Un pages ke liye jo free mint, refund ya airdrop de rahe hain. Wallet connect karne se pehle ye pata karta hai ke site asal mein kya kar rahi hai.",  # 202
    "onchain-claim-reverse-engineering ke liye",  # 203
    "Rarity aur kharidna",  # 204
    "nft-rarity-engine",  # 205
    "Collection ko rarity ke hisaab se rank karta hai",  # 206
    "Har NFT ko score karta hai aur unhi maths se order karta hai jo OpenSea use karta hai, to ranks match karte hain. OpenSea ke khud update hone se pehle reveal pakad sakta hai.",  # 207
    "nft-rarity-engine ke liye",  # 208
    "rh-chain-rarity-sniping",  # 209
    "Rare wale saste mein kharidta hai",  # 210
    "Reveal ke baad, normal floor price par listed sab se rare items dhoondta hai aur kisi ko pata chalne se pehle kharid leta hai.",  # 211
    "rh-chain-rarity-sniping ke liye",  # 212
    "nft-secondary-buy",  # 213
    "Aap ke liye listed NFT kharidta hai",  # 214
    "Resale market se kharidta hai, aur hamesha pehle purchase test karta hai taake kharab order par aap ki fee na lage.",  # 215
    "nft-secondary-buy ke liye",  # 216
    "Ye cheez asli hai?",  # 217
    "nft-minter-legitimacy-audit",  # 218
    "Check karta hai ke kharidne wale asli thay",  # 219
    "Dekhta hai ke kis ne mint kiya aur batata hai ke woh asli log thay ya kuch wallets jo popular dikhne ke liye interest fake kar rahe thay.",  # 220
    "nft-minter-legitimacy-audit ke liye",  # 221
    "web3-claim-verification",  # 222
    "Project ke claims ki fact-check karta hai",  # 223
    "Jab koi project kahe \"hum ne X kiya\", to ye blockchain par check karta hai ke sach hai ya nahi.",  # 224
    "web3-claim-verification ke liye",  # 225
    "nft-market-analysis",  # 226
    "Market ko sach ke saath parhta hai",  # 227
    "Floors, sales, holders, aur cheezein kitni tezi se flip hoti hain. Numbers asal mein kya kehte hain.",  # 228
    "nft-market-analysis ke liye",  # 229
    "nft-collection-price-analysis",  # 230
    "Collection ka andaza lagata hai",  # 231
    "Is ki value kya hai, kharidne ke baad kya ghalat ho sakta hai, aur risk ke hisaab se price theek hai ya nahi.",  # 232
    "nft-collection-price-analysis ke liye",  # 233
    "nft-exit-discipline",  # 234
    "Kab bechein",  # 235
    "Profit lene ke rules, hamesha hold karne ki jagah. Boring lagti hai lekin sab se zyada paisa bachati hai.",  # 236
    "nft-exit-discipline ke liye",  # 237
    "ethereum-wallet-operations",  # 238
    "Wallets safe tareeqe se banata aur move karta hai",  # 239
    "Naye wallets banata hai, keys ka sahi backup leta hai, aur tokens ko kabhi expose kiye baghair move karta hai.",  # 240
    "ethereum-wallet-operations ke liye",  # 241
    "wallet-radar-operations",  # 242
    "Un wallets par nazar rakhta hai jo aap ke liye ahem hain",  # 243
    "Khaas wallets follow karta hai aur jab woh kuch kharidein to aap ko ping karta hai.",  # 244
    "wallet-radar-operations ke liye",  # 245
    "public-wallet-xlsx-delivery",  # 246
    "Wallets ko spreadsheet mein badalta hai",  # 247
    "Wallets ki list leta hai aur saaf, share karne layak spreadsheet deta hai.",  # 248
    "public-wallet-xlsx-delivery ke liye",  # 249
    "pseudonym-identity-research",  # 250
    "Anonymous accounts ko jorta hai",  # 251
    "Un anonymous handles aur wallets ko link karta hai jo ek hi bande ke hain.",  # 252
    "pseudonym-identity-research ke liye",  # 253
    "Apna collection banana",  # 254
    "nft-collection-production",  # 255
    "Collection zero se banata hai",  # 256
    "Art plan, traits, pricing, mint page aur contract mechanics, sab ek jagah.",  # 257
    "nft-collection-production ke liye",  # 258
    "nft-trait-taxonomy",  # 259
    "Traits ko organise karta hai",  # 260
    "Har attribute ko consistent aur grouped rakhta hai taake aap ka metadata gadbad na ban jaye.",  # 261
    "nft-trait-taxonomy ke liye",  # 262
    "nft-trait-curation",  # 263
    "Trait ki quality check karta hai",  # 264
    "Launch se pehle har trait ko duplicates aur kisi bhi ghalat lagne wali cheez ke liye check karta hai.",  # 265
    "nft-trait-curation ke liye",  # 266
    "Tools aur research",  # 267
    "ethereum-data-pipelines",  # 268
    "Blockchain ko free mein parhta hai",  # 269
    "API ke paise diye baghair on-chain data nikalta hai. Bohat si doosri skills ka engine.",  # 270
    "ethereum-data-pipelines ke liye",  # 271
    "rh-mint-command-center",  # 272
    "Mint ka control room",  # 273
    "Minting ke liye local dashboard: mint plan karein, rehearse karein, wallets ka set manage karein, floor dekhein, aur baad mein dekhein ke kya hua.",  # 274
    "rh-mint-command-center ke liye",  # 275
    "mint-field-guide",  # 276
    "Mint dashboard",  # 277
    "Aane wale mints aur market movement ki read-only screen, jismein likha hota hai ke har number kahan se aaya.",  # 278
    "mint-field-guide ke liye",  # 279
    "pow-mint-mining",  # 280
    "Solved mints ko handle karta hai",  # 281
    "Hashcats, FAB4200 aur aise doosre paise dene ki jagah lucky number dhoondne par item dete hain. Ye woh search aap ke liye chalata hai.",  # 282
    "pow-mint-mining ke liye",  # 283
    "onchain-puzzle-mining",  # 284
    "Numbers ka kaam",  # 285
    "Woh search aap ki machine par ya kiraye ke hardware par chalata hai, check ke saath taake koi transaction zaya na ho.",  # 286
    "onchain-puzzle-mining ke liye",  # 287
    "onchain-puzzle-solving",  # 288
    "Aise mints solve karta hai jinmein dimagh lagta hai",  # 289
    "Kuch drops ko rokne wali paheliyan aur chhupe clues, game ke apne code ko parh kar dhoonde jate hain.",  # 290
    "onchain-puzzle-solving ke liye",  # 291
    "onchain-game-economy-analysis",  # 292
    "Game ki economy ka naqsha banata hai",  # 293
    "On-chain game ko khol kar dikhata hai ke value kahan se aati hai.",  # 294
    "onchain-game-economy-analysis ke liye",  # 295
    "polymarket",  # 296
    "Prediction markets parhta hai",  # 297
    "Check karta hai ke betting markets kisi event ki kya price laga rahe hain.",  # 298
    "polymarket ke liye",  # 299
    "proof-of-play-archive",  # 300
    "Proof of Play research",  # 301
    "Proof of Play aur Pirate Nation par background research.",  # 302
    "proof-of-play-archive ke liye",  # 303
    "agent-protocol-identity",  # 304
    "Agent ko ek identity deta hai",  # 305
    "Agent ko online post karte waqt sabit karne deta hai ke woh kaun hai, taake asli ko fake se pehchana ja sake.",  # 306
    "agent-protocol-identity ke liye",  # 307
    "flop-technocore-agent-ops",  # 308
    "Agent ko public mein chalana",  # 309
    "Agent ko apna account kaise dein aur kuch private leak kiye baghair post kaise karwayein.",  # 310
    "flop-technocore-agent-ops ke liye",  # 311
    "internet-computer-development",  # 312
    "Internet Computer par banana",  # 313
    "Ek doosri blockchain, Internet Computer, ke liye notes.",  # 314
    "internet-computer-development ke liye",  # 315
    "Koi matching skill nahi mili. Doosra term ya category try karein.",  # 316
    "Sab skills dikhayein",  # 317
    "Hashcats mint karein (aur aise drops)",  # 318
    "Kuch drops ki koi price nahi hoti. Paise dene ki jagah aap ko ek lucky number dhoondna hota hai,\n    aur jo pehle dhoond le wohi cat le jata hai. Jab log kehte hain ke mint kharida nahi, solve kiya jata hai, to matlab yahi hota hai.",  # 319
    "Aap ka laptop ye kar sakta hai, lekin din lag jayenge, aur bade kiraye ke computers wale minute\n    mein dhoond lete hain. To aap kuch minute ke liye ek kiraye par lete hain. Is sab ki sirf yahi wajah hai.",  # 320
    "Kuch minute ke liye computer kiraye par lein (shuru karna free)",  # 321
    "Modal",  # 322
    "second ke hisaab se computers kiraye deta hai. Aap kuch nahi kharidte. Aap sign up karte hain\n    aur is ke saath milta hai",  # 323
    "har mahine $30 ka free computing",  # 324
    ", jo taqreeban saat\n    ghante un ki tez machines ka hota hai, lagbhag $4 fi ghanta. Kabhi kabhi try karne ke liye aap\n    ko shayad kabhi paise nahi dene parenge.",  # 325
    "Free sign up karein",  # 326
    "modal.com",  # 327
    ".\n      $30 pehle se shamil hai.",  # 328
    "Phir ye do commands ek baar chalayein:",  # 329
    "Doosra browser kholta hai aur aap ka account link karta hai. Poora setup bas itna hai.",  # 330
    "Discord mein kya likhna hai",  # 331
    "Poora kaam bas itna hai. Apne bot ko mention karein aur ye paste karein:",  # 332
    "Ye round ki report aap ko deta hai. Jab waqai koshish karni ho:",  # 333
    "Aur ye dekhne ke liye ke kya hua:",  # 334
    "Ye aap ke liye kya sambhalta hai",  # 335
    "Pehle poora setup check karta hai, to koi run kharab haalat mein shuru nahi hota",  # 336
    "Searching kiraye ke computer par karta hai, aap ke computer par nahi",  # 337
    "Kuch kharch karne se pehle har jawab check karta hai, taake der se aane wale jawab par aap ki fee na lage",  # 338
    "Transaction aap ke wallet se bhejta hai aur link aap ko deta hai",  # 339
    "Sirf do kaam jo aap hi kar sakte hain",  # 340
    "Apne wallet mein thora ETH daalein.",  # 341
    "Jeetne par bhi fees mein kuch cents lagte hain. Woh hissa koi aap ke liye nahi kar sakta.",  # 342
    "Koshishein chhoti rakhein.",  # 343
    "Rounds musalsal badalte rehte hain, aur jo round khatam ho chuka us ka kaam zaya jata hai. Chhoti aur baar baar wali koshish ek lambi run se behtar hai.",  # 344
    "Odds ke baare mein sach kehein.",  # 345
    "Aap un sab se race kar rahe hain jo wohi drop try kar rahe\n    hain, aur jeetein ya haarein, computing ke paise aap dete hain. Free credit isi ke liye hai.\n    Ise use karein, koshishein chhoti rakhein, aur guaranteed cat ki umeed par paise na daalein.",  # 346
    "Doosre drops jahan ye kaam karta hai",  # 347
    "Wohi idea aur wohi tarah ka prompt. Aap sirf apna wala naam lein:",  # 348
    "Koi khaas wording nahi hai.",  # 349
    "Link paste karein aur batayein aap kya chahte hain.",  # 350
    "Ek\n    OpenSea link, ek tweet, ek mint website, ek wallet address, ek contract address.\n    Agar samajh na aaye ke aap ka matlab kya hai, to ye pooch leta hai.",  # 351
    "OpenSea link paste karein",  # 352
    "Ek tweet paste karein jismein likha ho \"ye mint karein\"",  # 353
    "Ye sab se kaam ki cheez hai. Tweet daalein aur ye pata kar leta hai ke mint kya hai, asal mein\n    kitne paise lagte hain, abhi bhi khula hai ya nahi, aur project asli lagta hai ya nahi — ye sab\n    wallet ko chhune se pehle.",  # 354
    "Ye seedha transaction nahi bhej deta. Tweet parhta hai, contract dhoondta hai, price aur\n    supply on-chain check karta hai, jo mila woh aap ko dikhata hai, aur aap ke haan kehne ka\n    intezar karta hai.",  # 355
    "Mint website paste karein, ya sirf ek contract address",  # 356
    "Wallet address paste karein",  # 357
    "Ise kehein ke aap ke liye kisi cheez par nazar rakhe",  # 358
    "Ise kehein ke aap ke liye kharide ya mint kare",  # 359
    "In mein se har ek pehle check karta hai aur kuch karne se pehle cost batata hai. Jab tak aap\n    haan na kahein, kuch nahi hota.",  # 360
    "Ise kehein ke koi cheez samjhaye",  # 361
    "Aam usool:",  # 362
    "agar aap usay paste kar sakte hain, to ye us par nazar daal sakta\n    hai. Links, screenshots, addresses, tweets, spreadsheets. Agar samajh na aaye ke kaise poochna\n    hai, to bas batayein aap kya karna chahte hain aur baqi ye khud samajh lega.",  # 363
    "Kisi skill ka apna kaam badalna chahte hain?",  # 364
    "Woh alag page hai, kyunke\n    yahan seekhne wali sab se kaam ki cheez wohi hai:",  # 365
    "baat kar ke skills behtar banayein",  # 366
    "Vercel setup karein",  # 367
    "Vercel internet par free mein website ya page daalta hai. Agent chalane ke liye iski zarurat\n    nahi. Iski zarurat tab hai jab aap ko apna public page chahiye: share karne wala link,\n    portfolio, documentation page, ye guide.",  # 368
    "Account banayein",  # 369
    "Sign up karein",  # 370
    "vercel.com/signup",  # 371
    "GitHub, Google ya email se. Yahan sab kuch ke liye free plan kaafi hai.",  # 372
    "Aasan tareeqa: GitHub project connect karein",  # 373
    "Vercel mein click karein",  # 374
    "Add New → Project",  # 375
    "Apna GitHub account connect karein aur woh repository chunein jo online karni hai.",  # 376
    "Agar aap ki web files top level ki jagah kisi folder mein hain, to set karein",  # 377
    "Root\n      Directory",  # 378
    "us folder par. Is guide ke page ka woh folder ye hai",  # 379
    "Click karein",  # 380
    "Deploy",  # 381
    ". Ek minute baad aap ke paas live link hoga.",  # 382
    "Is ke baad jab bhi aap GitHub par push karein, Vercel khud site dobara build kar deta hai.\n    Poora workflow bas itna hai.",  # 383
    "Terminal wala tareeqa",  # 384
    "Agar aap seedha apne computer se deploy karna chahein:",  # 385
    "Pehli baar do chaar sawal poochta hai aur phir aap ka live link print karta hai.",  # 386
    "Test ke liye is guide ka page deploy karein",  # 387
    "Apna domain",  # 388
    "Optional. Project ke",  # 389
    "Settings → Domains",  # 390
    "mein aap apna domain add kar sakte hain, ya jo free",  # 391
    "address ye deta\n    hai usay accept kar lein.",  # 392
    "Vercel kya nahi kar sakta:",  # 393
    "aap ka agent chalana. Vercel sirf woh websites serve karta hai jo\n    on demand load hoti hain. Aap ka agent ek program hai jo on rehna hota hai, is liye ye aap ke\n    computer ya server par rehta hai. Agar kabhi deploy aise fail ho",  # 394
    "error ke saath, to woh account free plan ki transfer allowance se aage nikal gaya hai.\n    Naya project banayein, ya GitHub Pages ya Cloudflare Pages use karein, jo wohi files serve karte hain.",  # 395
    "Aap ka computer, server, ya hosted?",  # 396
    "Dono chalte hain. Asal farq sirf ye hai ke laptop band karne par kya hota hai.",  # 397
    "FREE",  # 398
    "Apne computer par",  # 399
    "Jo install aap kar chuke hain, us ke ilawa kuch setup nahi karna",  # 400
    "Poori speed, aur ye sirf aap ki cheezein use kar sakta hai: aap ka browser, aap ki files, aap ke wallets",  # 401
    "Lid band karne par ruk jata hai",  # 402
    "ya sleep mein daalein",  # 403
    "Koi bhi scheduled job, alert ya raat bhar ki watch apna waqt kho deti hai",  # 404
    "In ke liye behtar: kuch try karna, din mein use karna, woh cheezein jo aap khud dekh rahe hain",  # 405
    "~$5 / MONTH",  # 406
    "Ek chhote server par",  # 407
    "Kabhi sota nahi. Ek baar start kiya to chalta rehta hai",  # 408
    "Watches, alerts aur timed jobs raat 4 baje bhi waqai chalte hain",  # 409
    "Aap kisi bhi jagah se apne phone par Discord ke zariye is tak pohanch sakte hain",  # 410
    "Koi screen nahi, to chat ke ilawa ye kaam karta hua nazar nahi aata",  # 411
    "In ke liye behtar: scheduled jobs, raat bhar ki watches, woh sab jo aap hamesha chalte dekhna chahte hain",  # 412
    "PORTAL PAR PRICING",  # 413
    "Ya Nous se host karwayein",  # 414
    "Hermes Cloud",  # 415
    "aap ke liye instance chalata hai",  # 416
    "Koi server khud setup, patch ya restart nahi karna",  # 417
    "Ise web page se, ya apne agent se keh kar start, stop aur restart karein",  # 418
    "Discord setup wohi jo har jagah hai",  # 419
    "In ke liye behtar: woh log jo server bilkul nahi chalana chahte",  # 420
    "Ya Nous se host karwayein",  # 421
    "Agar server chalana aisa kaam lagta hai jo aap nahi karna chahte,",  # 422
    "Nous Research\n    Hermes Cloud instances host karta hai",  # 423
    ". Aap ko hamesha on rehne wala agent milta hai, bina\n    provider chune, bina box secure kiye aur bina usay update rakhe.",  # 424
    "Banayein",  # 425
    "Nous Portal",  # 426
    "account yahan",  # 427
    "portal.nousresearch.com",  # 428
    "Kholein",  # 429
    "Agents",  # 430
    "page aur ek instance banayein. Ise koi naam dein.",  # 431
    "Discord ko is se bilkul step 03 ki tarah connect karein. Wohi commands, instance par\n      chalayein.",  # 432
    "Is ke baad aap usay usi web page se manage karte hain. Wahan se start, stop, restart ya delete\n    karein. Pricing Portal par plans ke saath likhi hoti hai.",  # 433
    "Ek hi subscription dono kaam kar sakti hai.",  # 434
    "Portal plan alag model subscription ki jagah agent ka dimagh bhi ban\n    sakta hai: ismein models ka bara catalogue plus managed web search, image generation aur voice\n    shamil hai, sab ek hi login se. Chalayein",  # 435
    "aur ye khud set up\n    ho jata hai. Agar aap pehle se OpenCode ke paise de rahe hain to dono ki zarurat nahi.",  # 436
    "Pehle se agent locally chala rahe hain?",  # 437
    "Aap website par clicks karne ki jagah apne agent se keh kar cloud instances manage kar sakte\n    hain. Ek command aap ke local agent ko Portal se connect karti hai:",  # 438
    "Is ke baad aap keh sakte hain \"mere cloud agents list karein\", \"woh instance kitna kharcha\n    kar raha hai\", ya \"jo ruk gaya hai usay restart karein\".",  # 439
    "Server par shift hona",  # 440
    "Hetzner ya DigitalOcean se ek lein, taqreeban $5/month. Chunein",  # 441
    "Ubuntu",  # 442
    "system ke\n      liye. Sab se chhota option kaafi hai.",  # 443
    "Step 02 wali wohi Linux install line apne computer ki jagah us server par\n      chalayein.",  # 444
    "Wahan Discord aur skills ke steps dobara karein. Wohi teen commands hain.",  # 445
    "Aap dono chala sakte hain. Aap ka computer aur server alag agents hain, aur chahein to har ek ka\n      apna Discord bot token hota hai.",  # 446
    "Samajhdari wala tareeqa:",  # 447
    "aaj apne computer par shuru karein, aur server sirf tab kiraye par lein jab aap ke\n    paas kuch aisa ho jo sote waqt bhi chalna chahiye.",  # 448
    "Cheez",  # 449
    "Zaruri?",  # 450
    "Hermes agent",  # 451
    "Haan",  # 452
    "31 skills",  # 453
    "OpenCode subscription",  # 454
    "Haan, yehi dimagh hai",  # 455
    "Vercel",  # 456
    "Sirf agar aap online page chahte hain",  # 457
    "Apna computer",  # 458
    "Theek hai, lekin ye sota hai",  # 459
    "Chhota server",  # 460
    "Sirf chaubees ghante chalane ke liye",  # 461
    "Modal, Hashcats jaise drops solve karne ke liye",  # 462
    "Free, $30/month shamil",  # 463
    "Sirf agar aap un drops ke peeche jana chahte hain",  # 464
    "Nous Portal, hosting shamil",  # 465
    "Portal par likha hai",  # 466
    "Apne server ki jagah, aur ye dimagh bhi ban sakta hai",  # 467
    "Sach bola to total:",  # 468
    "taqreeban $10 maheena",  # 469
    ", ya $15 agar aap chahte hain ke ye raat bhar bhi jaagta rahe.",  # 470
    "Agar kuch ghalat ho jaye",  # 471
    "Aap ko kya dikhta hai",  # 472
    "Kya karein",  # 473
    "pehchana nahi jata",  # 474
    "Terminal band karein aur nayi kholein. Phir bhi fail ho? Computer restart karein aur dobara try karein.",  # 475
    "Bot online hai lekin kabhi jawab nahi deta",  # 476
    "Discord developer page par Message Content Intent off hai. Yeh sab se bara sabab hai.",  # 477
    "DMs mein jawab deta hai, server mein khamosh",  # 478
    "Normal hai. Servers mein ye sirf @mention par jawab deta hai.",  # 479
    "Kehta hai ke aap ko ijazat nahi",  # 480
    "Aap ki Discord user ID ghalat hai. Developer Mode on kar ke dobara copy karein.",  # 481
    "Vercel deploy 402 ke saath fail hota hai",  # 482
    "Woh account free transfer allowance se aage nikal gaya. Naya project, ya GitHub Pages ya Cloudflare Pages use karein.",  # 483
    "Agent raat bhar mein ruk gaya",  # 484
    "Ye aap ke computer par tha. Aisa hona normal hai. Agar hamesha on chahiye to ise server par le jayein.",  # 485
    "Ye aap se aur paise maangta hai",  # 486
    "Apna OpenCode usage page check karein. Lambe jobs chat se zyada kharch karte hain.",  # 487
    "Skills nazar nahi aati",  # 488
    "ye confirm karne ke liye ke install hui, phir",  # 489
    "chat mein.",  # 490
    "Samajh nahi aa raha",  # 491
    "Chalayein",  # 492
    "aur bas batayein aap kya karna chahte hain.",  # 493
    "Aap ka agent bas ek setup door hai.",  # 494
    "Guide aur sab 31 skills free hain. Ek model subscription connect karein, steps follow karein, aur ise apna bana lein.",  # 495
    "OpenCode lein",  # 496
    "Toolkit lein",  # 497
    "OpenCode ka link referral link hai. Is se sign up karna is project ko support karta hai.",  # 498
    "Aap ka banane ke liye bana.",  # 499
    "GitHub par source",  # 500
    "Skills ki vibe coding",  # 501
    "Guide par wapas",  # 502
    "Free aur open source. Yahan kuch bhi financial advice nahi hai. Minting aur trading mein paisa doob sakta hai. Shuru karne se pehle limit set karein aur kabhi woh paisa use na karein jo aap ko chahiye.",  # 503
]

# --------------------------------------------------------------------------
# attrs: one value per entry of strings.json["attrs"], same order
# --------------------------------------------------------------------------
ATTR = [
    "NFT toolkit ka home page",  # 1
    "Main navigation",  # 2
    "NFT toolkit GitHub par dekhein",  # 3
    "Agent ki baat cheet ki misaal",  # 4
    "Misal ka jawab",  # 5
    "Ek misaal chunein",  # 6
    "Aap ka setup teen steps mein",  # 7
    "Guide navigation",  # 8
    "Guide ke chapters",  # 9
    "What you need complete mark karein",  # 10
    "Scroll hone wali reference table",  # 11
    "Set up Hermes complete mark karein",  # 12
    "Aap ka operating system",  # 13
    "Settings file",  # 14
    "Set up Discord complete mark karein",  # 15
    "Download the skills complete mark karein",  # 16
    "rarity, wallets ya minting try karein…",  # 17
    "Skills ko category se filter karein",  # 18
    "Discord prompt",  # 19
    "Shuru karein",  # 20
    "Upar jayein",  # 21
]

# --------------------------------------------------------------------------
# head: keyed by strings.json["head"] keys
# --------------------------------------------------------------------------
HEAD = {
    "title": "NFT toolkit | Aap ka onchain agent, Discord mein",
    "description": "Apna Hermes agent 31 free NFT skills ke saath setup karein. Discord se mints research karein, collections rank karein aur wallets follow karein. Ek practical, step by step guide.",
    "og:title": "Onchain skills. Aap ke Discord mein.",
    "og:description": "Aap ka apna AI agent. 31 free NFT skills. Ek hi baat cheet. Poori setup guide se shuru karein.",
}

# --------------------------------------------------------------------------
# js: keyed by the English js_defaults keys
# --------------------------------------------------------------------------
JS = {
    "copy.discord": "Discord prompt copy karein",
    "copy.terminal": "Terminal command copy karein",
    "copy.button": "Copy",
    "copy.done": "Copy ho gaya",
    "copy.aria": "Clipboard par copy ho gaya",
    "toast.copied": "Copy ho gaya. Jab tayyar hon to paste kar lein.",
    "toast.manual": "Khud se copy nahi ho saka. Text select kar diya gaya hai, aap ise copy kar sakte hain.",
    "progress.count": "4 mein se {n}",
    "progress.saved": "Is browser mein save hai",
    "progress.visit": "Progress sirf is visit ke liye save hai",
    "toast.complete": "Setup mukammal. Agla step: apne agent ko ek message bhejein.",
    "skills.one": "skill",
    "skills.many": "skills",
    "skills.ready": "kaam par lagane ke liye",
    "skills.found": "mili",
    "demo.rarity.prompt": "is collection ko rank karein aur rare wale dikhayein",
    "demo.rarity.answer": "Collection rank ho gayi. Ye teen sab se rare hain.",
    "demo.rarity.title": "Rarity report",
    "demo.rarity.subtitle": "Demo collection",
    "demo.rarity.foot": "Sirf research. Koi transaction nahi bheji gayi.",
    "demo.mint.prompt": "wallet connect karne se pehle ye mint check karein",
    "demo.mint.answer": "Pehle contract, price aur supply check karta hoon.",
    "demo.mint.title": "Mint research",
    "demo.mint.subtitle": "Misaal checklist",
    "demo.mint.foot": "Mint approve karne se pehle findings dekhein.",
    "demo.mint.row1": "Asal contract verify karein",
    "demo.mint.row2": "Onchain mint price parhein",
    "demo.mint.row3": "Baqi supply check karein",
    "demo.mint.tag": "Pehle check",
    "demo.wallet.prompt": "ye wallet haal hi mein kya kharid raha hai?",
    "demo.wallet.answer": "Wallet ki public activity ka report bana deta hoon.",
    "demo.wallet.title": "Wallet intelligence",
    "demo.wallet.subtitle": "Misaal report",
    "demo.wallet.foot": "Public wallet data. Private keys ki zarurat nahi.",
    "demo.wallet.row1": "Haal hi ki kharidari",
    "demo.wallet.row2": "Rakhe hue collections",
    "demo.wallet.row3": "Sales aur transfers",
    "demo.wallet.tag": "Onchain",
}


def main():
    with open(SRC, encoding="utf-8") as f:
        src = json.load(f)

    # keys must be the untouched English source strings
    assert len(TEXT) == len(src["strings"]), (len(TEXT), len(src["strings"]))
    assert len(ATTR) == len(src["attrs"]), (len(ATTR), len(src["attrs"]))
    missing_head = [k for k in src["head"] if k not in HEAD]
    assert not missing_head, missing_head
    missing_js = sorted(set(src["js_defaults"]) - set(JS))
    extra_js = sorted(set(JS) - set(src["js_defaults"]))
    assert not missing_js, ("missing js keys", missing_js)
    assert not extra_js, ("extra js keys", extra_js)

    text = dict(zip(src["strings"], TEXT))
    attr = dict(zip(src["attrs"], ATTR))
    head = {k: HEAD[k] for k in src["head"]}

    out = {
        "lang": "ur-Latn",
        "name": "Urdu (Roman)",
        "dir": "ltr",
        "text": text,
        "attr": attr,
        "head": head,
        "js": JS,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("wrote", OUT)
    print("text", len(text))
    print("attr", len(attr))
    print("head", len(head))
    print("js", len(out["js"]))


if __name__ == "__main__":
    main()
