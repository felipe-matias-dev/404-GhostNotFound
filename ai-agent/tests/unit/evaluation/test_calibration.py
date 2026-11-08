from venergy_agent.evaluation.calibration import agreement, read_human_scores


def test_agreement_follows_the_dec_047_criterion():
    judge = {"G1": 5, "G2": 4, "G3": 2, "G4": 3}
    human = {"G1": 5, "G2": 3, "G3": 2, "G4": 4}

    result = agreement(judge, human)

    assert result.items == 4
    assert result.same_passed == 2
    assert result.mean_absolute_difference == 0.5
    assert result.mean_signed_difference == 0.0
    assert result.meets_criterion is False


def test_the_criterion_needs_twelve_of_fifteen_and_at_most_one_point():
    judge = {f"G{n}": 5 for n in range(15)}
    human = {**judge, "G0": 3, "G1": 3, "G2": 3}

    result = agreement(judge, human)

    assert result.same_passed == 12
    assert result.meets_criterion is True


def test_items_without_a_human_score_are_left_out():
    result = agreement({"G1": 5, "G2": 4}, {"G1": 5})

    assert result.items == 1


def test_human_scores_are_read_from_the_filled_sheet(tmp_path):
    sheet = tmp_path / "notas.csv"
    sheet.write_text("id;nota_humana\nG1;5\nG2;\nG3;2\n", encoding="utf-8")

    assert read_human_scores(sheet) == {"G1": 5, "G3": 2}
