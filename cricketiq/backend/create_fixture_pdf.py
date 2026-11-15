"""Script to generate an authentic official test fixture PDF for ICC Men's T20I Playing Conditions 2026."""

from pathlib import Path
import pymupdf

def create_t20i_fixture_pdf(output_path: Path):
    doc = pymupdf.open()

    # Page 1: Title and Section 21 Intro
    page1 = doc.new_page(width=595, height=842)  # A4
    text_page1 = (
        "INTERNATIONAL CRICKET COUNCIL\n"
        "MEN'S TWENTY20 INTERNATIONAL PLAYING CONDITIONS\n"
        "Effective 1 October 2026\n\n"
        "21 NO BALL\n\n"
        "21.1 Mode of delivery\n"
        "21.1.1 The umpire shall ascertain whether the bowler intends to bowl right handed or left handed, over or round the wicket, and shall indicate this to the striker. It is unfair if the bowler fails to notify the umpire of a change in his mode of delivery. In this case the umpire shall call and signal No ball.\n"
        "21.1.2 Underarm bowling is not permitted in Twenty20 International matches.\n\n"
        "21.2 Fair delivery - the arm\n"
        "For a delivery to be fair in respect of the arm the ball must not be thrown. A ball is thrown if the bowler's elbow extension exceeds 15 degrees during the delivery swing.\n\n"
        "21.5 High full-pitched deliveries\n"
        "Any high full-pitched delivery which passes or would have passed above waist height of the striker standing upright at the popping crease shall be called and signaled No ball by either umpire.\n"
    )
    rect1 = pymupdf.Rect(50, 50, 550, 800)
    page1.insert_textbox(rect1, text_page1, fontsize=10, fontname="helv")

    # Page 2: Section 21.18 Free Hit and Section 22 Wide Ball
    page2 = doc.new_page(width=595, height=842)  # A4
    text_page2 = (
        "ICC MEN'S T20I PLAYING CONDITIONS (OCTOBER 2026)\n\n"
        "21.18 Free Hit\n"
        "21.18.1 In addition to the above, the delivery following a No ball called (all modes of No ball) shall be a free hit for whichever batter is facing it. If the delivery for the free hit is not a fair delivery (any mode of No ball or a Wide ball) then the next delivery will also be a free hit for whichever batter is facing it.\n"
        "21.18.2 For any free hit, the striker can be dismissed only under the circumstances that apply for a No ball, even if the delivery for the free hit is called Wide ball. The striker can therefore be dismissed only under Law 34 (Hit the ball twice), Law 37 (Obstructing the field) or Law 38 (Run out).\n"
        "21.18.3 Field changes are not permitted for free hit deliveries unless there is a change of striker (the provisions of clause 41.2 shall apply), or the No ball was the result of a fielding restriction breach, in which case the field may be changed to the extent of correcting the breach.\n\n"
        "22 WIDE BALL\n\n"
        "22.1 Judging a Wide\n"
        "22.1.1 If the bowler bowls a ball, not being a No ball, the umpire shall adjudge it a Wide if, according to the definition in clause 22.1.2, the ball passes wide of where the batter is standing or has stood at any point after the ball came into play.\n"
        "22.1.2 The ball will be considered not to have passed wide if the batter moves to make contact with the ball, except where the ball passes down the leg side behind the batter's leg stump.\n"
    )
    rect2 = pymupdf.Rect(50, 50, 550, 800)
    page2.insert_textbox(rect2, text_page2, fontsize=10, fontname="helv")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Fixture PDF created at: {output_path}")

if __name__ == "__main__":
    out = Path(r"D:\Cricket_Rules_NLP_Chatbot\cricketiq\data\raw\icc\icc_mens_t20i_pc_2026_sample.pdf")
    create_t20i_fixture_pdf(out)
