import PIL
from PIL import Image
from pathlib import Path
import sdl2
import sdl2.ext
import copy
import typing
import os
import sys
from animearena.ability import Ability
if typing.TYPE_CHECKING:
    from animearena.effects import Effect
def resource_path(relative_path):
    try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
RESOURCES = Path(__file__).parent.parent.parent / "resources"

class Character:

    profile_image: Image
    name: str
    main_abilities: list[Ability]
    alt_abilities: list[Ability]
    current_abilities: list[Ability] = []
    altprof1: Image
    altprof2: Image
    main_prof: Image
    desc: str = ""
    selected: bool
    energy_contribution: int
    targeted: bool
    invulnerable: bool
    isolated: bool
    dead: bool
    full_dr: int
    untargetable: bool
    acted: bool
    stunned: bool
    ignoring: bool
    hp: int
    damage_reduction: int
    sistema_CAI_stage: int
    current_effects: list["Effect"]

    def __init__(self, name:str, desc:str = None):
        self.name = name
        if desc:
            self.desc = desc
        self.sistema_CAI_stage = 1
        self.energy_contribution = 1
        self.hp = 100
        self.full_dr = 0
        self.invulnerable = False
        self.isolated = False
        self.dead = False
        self.untargetable = False
        self.acted = False
        self.stunned = False
        self.ignoring = False
        self.selected = False
        self.damage_reduction = 0
        self.current_effects = []
        self.profile_image = Image.open(resource_path(RESOURCES / (name + "prof.png")))
        self.main_prof = Image.open(resource_path(RESOURCES / (name + "prof.png")))
        try:
            self.altprof1 = Image.open(resource_path(RESOURCES / (name + "altprof1.png")))
            self.altprof2 = Image.open(resource_path(RESOURCES / (name + "altprof2.png")))
        except:
            pass

        self.main_abilities = [Ability(f"{name}{i + 1}") for i in range(4)]
        self.current_abilities = self.main_abilities
        self.alt_abilities = []
        for i in range(4):
            try:
                self.alt_abilities.append(Ability(f"{name}alt{i + 1}"))
            except FileNotFoundError:
                break

def get_character(name: str):
    return copy.copy(character_db[name])
        
character_db = {"naruto": Character("naruto", "Uzumaki Naruto, a former outcast of the Hidden Leaf Village, struggled throughout" +
                " his life to become the type of ninja that the village could accept. Now, after training under Kakashi Hatake, Jiraiya," +
                " and the toad sages of Mount Myoboku, he is ready to prove himself against his village's enemies."),
                "hinata": Character("hinata","Hyuga Hinata, a shy kunoichi from the Leaf Village's legendary Hyuga clan. After a chance meeting with Uzumaki Naruto changes her life, Hinata resolves to stay true to herself and follow the path" +
                " she believes in. She develops a unique version of the Hyuga's Gentle Fist that involves expelling her chakra from her bodies chakra points, shaping them into guardian lions."),
                "neji": Character("neji", "Hyuga Neji, a shinobi of the Leaf Village's Hyuga clan. Regarded as a genius despite being born into a lower caste of the family, Neji's prowess of the Byakugan and Gentle Fist taijutsu is unmatched among the Hyuga clan."),
                "shikamaru": Character("shikamaru", "Nara Shikamaru, a jonin from the Hidden Leaf Village. A talented shinobi whose genius is only matched by his laziness. Shikamaru's clan specializes in jutsu that can manipulate shadows to debilitate their enemies."),
                "kakashi": Character("kakashi", "Kakashi Hatake, renowned ninja of the Hidden Leaf Village. A prodigiously skilled shinigami in his own right, " +
                "the addition of his childhood friend's Sharingan eye served to make him one of the most formidable shinobi of all time."),
                "minato": Character("minato", "Yamikaze Minato, the fourth Hokage of the Hidden Leaf Village. Minato gave his life protecting " +
                " the Leaf Village from the Nine-Tailed Fox, leaving it sealed inside his only son."),
                "itachi": Character("itachi","Uchiha Itachi, a prodigious ninja responsible for murdering nearly his entire clan. Using the Uchiha bloodline's legendary eye powers, in conjunction with mythic artifacts, " +
                "there are many who consider Itachi to be the most talented ninja in the world."),
                "ichigo": Character("ichigo","Kurosaki Ichigo, substitute shinigami protector of Karakura town, is the humanborn son of" +
                " a shinigami and a quincy. His zanpakutou Zangetsu can fire deadly projectiles and " +
                "increase his physical abilities for a short period."),
                "orihime": Character("orihime", "Orihime Inoue, a human girl who is dragged alongside Kurosaki Ichigo into the world of shinigami. She has a kind, compassionate personality, which manifests itself " +
                "as her six flowers, the Shun Shun Rikka. Using this innate gift, she can reject the natural state of the world in a myriad of ways."),
                "rukia": Character("rukia", "Kuchiki Rukia, the shinigami originally charged with the protection of Karakura town. After recovering in the Soul Society, " +
                "Rukia gains her original shinigami powers back, returning her ability to call on Sode no Shirayuki, a powerful ice-type zanpakutou."),
                "ichimaru": Character("ichimaru","Ichimaru Gin, the Captain of the Gotei 13's 3rd Squad. A sly, cunning shinigami, no one knows what's going on behind Ichimaru's stoic, grinning mask. Until the moment that he strikes, " +
                "there isn't a soul alive that can tell what Ichimaru is going to do."),
                "aizen": Character("aizen", "Sousuke Aizen, the betrayer of Soul Society. A shinigami of incredible power, Aizen's overwhelming strength and cunning are only augmented by his Zanpakutou's ability to control his enemies five senses."),
                "midoriya": Character("midoriya", "Midoriya Izuku was born quirkless, but he didn't let that stop him from" +
            " dreaming of being the world's number one hero. When he agrees to be the successor of All Might, the world's" +
            " current number one, he leaps headfirst into the world of heroes along with his inherited quirk, One For All."),
                "uraraka": Character("uraraka", "Uraraka Ochaco, a hero-in-training. Under the name Uravity, Uraraka, much like every student in UA's class 1-A, is doing her best to work towards a future where she can achieve her dream. Her Quirk, Zero Gravity, lets her make objects float" +
                " with a touch. This floating effect, combined with her innate tactical acumen, make her a skilled and versatile hero."),
                "todoroki": Character("todoroki", "Todoroki Shoto, a member of the class 1-A of the Hero Course at UA High School. The son of the number 2 hero, Shoto's life was very nearly thrust onto the wrong path due to his father's obsession with" +
                " birthing the hero who would seize the number one spot. After being helped by Midoriya Izuku, Shoto has hardened his resolve to become a worthy hero for his own reasons."),
                "mirio": Character("mirio", "The top student at UA, the number one school for heroes. Togata Mirio, who was once considered the best choice for One For All, can become insubstantial at will, and uses this " +
                "power to protect the people important to him and sweep through his enemies with overwhelming power."),
                "toga": Character("toga", "Himiko Toga is a psychopathic young member of the League of Villains. After a chance meeting, " +
                "she develops an obsessive crush on Midoriya Izuku, who she pursues whenever she can. Her Quirk, Transform, lets her " +
                "take on the shape of other humans by drinking their blood."),
                "shigaraki": Character("shigaraki", "Shigaraki Tomura, the head of the league of villains. Taken in at a young age by legendary villain All For One, Shigaraki's mind has been twisted and warped beyond " +
                "repair. Now, unsure of what he seeks, he cuts a swath of destruction and misery through the world of heroes."),
                "jiro": Character("jiro","Kyoka Jiro, the Hearing Hero Earphone Jack. A member of UA's Class 1-A, Jiro is an earnest young musician turned hero. Using her Quirk, Earphone Jack, she can scout out areas, detect incoming attacks, and " +
                "produce powerful shockwaves of overwhelming sound."),
                "natsu": Character("natsu", "Natsu Dragneel, infamous fire mage of Fairy Tail. He was raised by a dragon," +
                " Igneel, who taught him dragon-slaying magic that he wields with a pure heart and a quick temper."),
                "lucy": Character("lucy", "Lucy Heartfilia, proud Celestial Spirit wizard of Fairy Tail. After a chance meeting with Natsu Dragneel, Lucy joined his guild and started a life of adventure. As a Celestial Spirit wizard, Lucy uses Zodiac Keys to summon outsiders to fight with her."),
                "gray": Character("gray", "Gray Fullbuster, ice mage of Fairy Tail. Natsu's number one rival, Gray is a cool and collected mage that uses ice moulding magic to craft wondrous creations from ice."),
                "erza": Character("erza", "Erza Scarlet, one of Fairy Tail's strongest S-Class wizards. Known to the world as Titania, Queen of the Fairies, Erza uses Spatial magic to rapidly change between" +
                " extra-dimensionally stored armor and weapons. With an offensive and defensive tool for every situation, there are few foes in the entire world who can call themselves Erza's equal in battle."),
                "gajeel": Character("gajeel", "Gajeel Redfox, the Iron Dragon Slayer. Raised, like Natsu, by a mighty dragon, Gajeel is a proud and standoffish wizard of Fairy Tail. He can" +
                " make his body hard as iron and transform it into weapons to deal brutal blows."),
                "wendy": Character("wendy", "Wendy Marvell, the Sky Dragon Slayer. Raised by the dragon Grandeeney, Wendy is a timid, supportive girl " +
                "who values her friends and her guild above all other things. She wields both powerful wind techniques and support magic, making her" +
                " a formidable Fairy Tail wizard despite her shyness."),
                "levy": Character("levy","Levy McGarden, a wizard of Fairy Tail. Levy is a studious and shrewd wizard who always keeps a level head. Her versatile magic allows her to create magical effects" +
                " by writing solid words in the air and evoking them."),
                "laxus": Character("laxus","Laxus Dreyar, the grandson of the current Master of Fairy Tail. Implanted with Dragon Lacrima at a young age, Laxus is the Lightning Dragon Slayer, and a prodigiously" +
                " powerful mage in his own right. Though he once lost his way, he's never stopped considering the wizards of Fairy Tail to be his family."),
                "saber": Character("saber", "Saber, the Heroic Spirit Arturia Pendragon. The famous wielder of Excalibur, " +
                "Saber has top notch combat and defensive abilities and can go toe-to-toe with nearly any combatant. Her powerful blade" +
                " can demolish entire fortresses."),
                "chu": Character("chu", "Chu Chulainn, a Lancer-class Heroic Spirit, is a legendary figure from Irish folklore. Wielding the enchanted spear Gae Bolg, Chu" +
                " is a frighteningly skilled spearman capable of warding away weak attacks while piercing through enemy defences."),
                "astolfo": Character("astolfo", "Astolfo, one of the Twelve Paladins of Charlemagne, summoned in the role of Rider. A free-spirited individual, often to a fault, Astolfo picks his path moment by moment and follows it until the end. A lifetime " +
                "spent following his heart has left him inundated with Noble Phantasms from across the ages."),
                "jack": Character("jack","Jack the Ripper, a Heroic Spirit summoned in the role of Assassin. Jack is an embodiment of the vengeful spirits" +
                " of the lost and neglected children who died on the streets of London. She can call forth London's bleak smog and steal her enemies away to its cold streets."),
                "misaka": Character("misaka", "Misaka Mikoto, the ace of Tokiwadai Middle School. Misaka is one of seven Level 5" +
            " espers in Academy City, the world's bastion of esper research. Her abilities as an electromaster" +
            " have her ranked third among the city's top espers."),
                "kuroko": Character("kuroko", "Shirai Kuroko, level 4 esper and Misaka Mikoto's devoted underclassman. A talented member of Judgement, Academy City's organized esper task force, Kuroko " +
                "puts her all into her work, constantly improving while maintaining a strict code of justice. Her ability to teleport both objects and herself make her an unpredictable foe."),
                "sogiita": Character("sogiita","Sogiita Gunha, the seventh ranked esper in Academy City. His abilities defy understanding, though he personally believes that with " +
                "a little guts, anything is possible."),
                "misaki": Character("misaki", "Shokuhou Misaki, the fifth-ranked Level 5 esper in Academy City. Possessing the strongest mental ability, Mental Out, Misaki dislikes personal exertion and tends to accomplish her goals through the use of her mind-controlled thralls."),
                "frenda": Character("frenda","Frenda Seivelun, a Level-0 member of the dark side organization known as ITEM. A skilled mercenary, Frenda's personal talent allows her to operate in a world rife with powerful espers, despite her lack of psychic powers."),
                "naruha": Character("naruha","Sakuragi Naruha, a member of the Dark Side organization known as SCAVENGER. Naru can use her psychic powers to manipulate paper, preferring to utilize it in the construction of a massive rabbit suit. She, like the rest of SCAVENGER, " +
                "believes that all the problems in Academy City are caused by teachers, and hates them above all other things."),
                "tsunayoshi": Character("tsunayoshi", "Sawada Tsunayoshi, the tenth head of the Vongola Family. Unconfident and timid, yet fiercely" +
                " loyal to his friends, Tsuna is the unwilling head of a mafia family, and wielder of the Vongola Flames of the Sky."),
                "yamamoto": Character("yamamoto", "Yamamoto Takeshi, the Vongola Guardian of Rain. The heir to the Shigure Soen Ryu style of swordsmanship, " +
                "Yamamoto is a mild-mannered teenager who has more interest in enjoying his time with his friends than improving" +
                " the Vongola Mafia family."),
                "gokudera": Character("gokudera", "Hayato Gokudera, the Vongola Guardian of Storm. A fiercely loyal member of the Vongola family, Gokudera gives his all to serve Tsunayoshi and the mafia family he is reluctantly forming."),
                "ryohei": Character("ryohei", "Sasagawa Ryohei, the Vongola Guardian of the Sun. Ryohei is an exuberant, if slightly oblivious, member of Sawada Tsunayoshi's growing Mafia family. An avid boxer, " +
                "his motto is to live 'to the extreme!', which is something that he extends to all facets of life. He immediately and enthusiastically wants to be included in anything he sees."),
                "lambo": Character("lambo", "Lambo, the Vongolo Guardian of Lightning. Lambo's special skin allows him to absorb electricity, which he uses both in offense and to " +
                "fulfill his role as the lightningrod that redirects danger away from the rest of the Family. When things become too much for him, he can use the Ten-Year Bazooka " +
                "to call his older selves to the battlefield."),
                "hibari": Character("hibari", "Hibari Kyoya, the head of the disciplinary committee at Tsuna's High School. Hibari answers to no one, and though he lends his fierce combat " +
                "prowess to the Vongola cause, he does so on his own terms."),
                "chrome": Character("chrome","Dokuro Nagi, who goes by the alias Chrome. Along with Rokudo Mukuro, the master illusionist who shares her body, Chrome serves as the Vongola Family's Mist Guardian, weaving illusions and misdirections to " +
                "keep danger away from the family."),
                "tatsumi": Character("tatsumi", "Tatsumi, the newest member of Night Raid. Heading to the big city" +
                " with dreams of fame and fortune, Tatsumi's dreams are quickly dashed as he is introduced to" +
                " the darkness that lurks there. He decided to join Night Raid, a group of rebel assassins, to help make the " +
                "country a safe and just place for all."),
                "akame": Character("akame", "Akame, the most talented killer of the assassin group Night Raid. Raised from a young age by the corrupt Empire, a chance assignment saw Akame" +
                " turning on the nation that raised her. Now, she wields the fearsome blade Murasame to free the oppressed people from the tyranny of the Prime Minister."),
                "leone": Character("leone","Leone, an assassin of Night Raid. A former street urchin turned professional killer, Leone fights for the downtrodden and the neglected. Along with her Teigu, Lionel, she is determined to rip and tear a bloody swath " +
                "through the corrupt Empire until she can finally secure peace for hopeless."),
                "mine": Character("mine", "Mine, genius sniper of the assassin group Night Raid. Fiercely strong-willed, Mine wields the Teigu known as Pumpkin, a powerful rifle that" +
                " fires energy blasts which become more dangerous with the situation its wielder finds themselves in."),
                "raba": Character("raba", "Lubbock, an assassin working for Night Raid. With his wire Teigu 'Cross Tail', Lubbock is a versatile killer that can use razor-sharp threads to deliver lethal blows or defend his allies."),
                "seiryu": Character("seiryu", "Seiryu Ubiquitous, former member of the Imperial Guard. After Esdeath forms the Jaegers to hunt down Night Raid, Seiryu joins the group to get vengeance on the" +
                " criminals who killed her mentor. Twisted by the darkness in the capitol, and her own sense of justice, Seiryu uses her living Teigu 'Koro' to slay evil wherever she finds it."),
                "esdeath": Character("esdeath", "Esdeath, the strongest Teigu wielder in the Empire. The leader of the Empire's anti-Night Raid task force known as the Jaegers, Esdeath's ice-wielding powers " +
                "and bloodthirsty, unparalleled strength are the ultimate obstacle standing between the Revolutionary Army and peace."),
                "snowwhite": Character("snowwhite", "Himekawa Koyuki, the magical girl Snow White. A loving, selfless girl who " +
                "was drawn into a game of death by a sadistic magical girl. She can hear the thoughts of those in distress, and can" +
                " use this to aid allies or get the upper hand on enemies."),
                "pucelle": Character("pucelle","Kishibe Souta, the Magical Girl La Pucelle. As a boy, Souta often felt out of place due to his fascination with Magical Girls. He found a steady friendship in Himekawa Koyuki, and now that they are both Magical Girls, the two seek to live out their ideal lives, protecting the weak from harm."),                
                "ripple": Character("ripple", "Kano Sazanami is a serious high-school girl with a complicated home life. On the other hand, as the Magical Girl Ripple, she fights with reckless ferocity, often charging in head-on and relying on her enhanced accuracy to clinch victories. Despite these flaws, " +
                "Ripple tries her best to be a proper Magical Girl, and has the heart of a true hero."),
                "nemu": Character("nemu", "Sanjou Nemu, a 24-year-old NEET, found an opportunity to reinvent herself as the Magical Girl Nemurin. With her ability to enter the dreams of others, she fights to protect the realm of peaceful sleep."),
                "ruler": Character("ruler", "Sanae Mukou, a woman who spent her entire life being ostracized for her intellect and browbeat by incompetent authority, " +
                "received the opportunity to become the Magical Girl Ruler. Using her power to issue commands that must be obeyed, she has gathered a cluster of easily " +
                "manipulated magical girls to her side."),
                "swimswim": Character("swimswim", "Sakanagi Ayana, the Magical Girl Swim Swim. One of Ruler's subordinates, Swim Swim is a very young girl who idolizes princesses. She has the ability to become insubstantial and to dive through the ground like water which, when combined with her natural ruthlessness, makes her a terrifying foe."),
                "cmary": Character("cmary", "Yamamoto Naoko, the Magical Girl known as Calamity Mary. Unlike the other Magical Girls in N-City, Calamity Mary has no interest in working to help its citizens, instead lending her aid to the criminal Kannawa Association. Her magic lets her increase the capabilities of any weapon she wields."),
                "cranberry": Character("cranberry", "Cranberry, the Musician of the Forest. The first Magical Girl of N-City, Cranberry is a battle-hungry fanatic, trained by the world of magic into a fighter of nearly unparalleled skill. With the help of Fav, a mascot from the world of magic, she travels the world to orchestrate cruel death matches between Magical Girls, in the hopes of finding the strongest among them to fight."),
                "saitama": Character("saitama", "Saitama, the most powerful hero in the world. After a chance encounter forces him to come face to face with his own weakness, " +
                "Saitama trained with a singular purpose, to gain strength. Now, after having achieved his goal, he now forced to face an enemy more resilient than he could have imagined: his own overwhelming power."),
                "tatsumaki": Character("tatsumaki", "Tatsumaki, the Tornado of Terror, is the Hero Associations Rank 2 hero, and the most powerful esper in the world. She prefers to work alone, using her unparalleled psychic powers and " +
                "caustic personality to ward off both threats and allies."),
                "chachamaru": Character("chachamaru", "Chachamaru is a robot designed in the image of a high school girl. She serves as the combat partner to Evangeline A.K. McDowell, and serves her" +
                " loyally with a wide variety of versatile functions."),
                "mirai": Character("mirai", "Kuriyama Mirai, an isolated Spirit World Warrior. Mirai is the last of her clan, who were feared and reviled due to their ability to manipulate their cursed blood to use in battle.")
                
                
                }