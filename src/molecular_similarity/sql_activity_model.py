from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import Descriptors, MACCSkeys, rdFingerprintGenerator, rdMolDescriptors
from sklearn.linear_model import LogisticRegression


DEFAULT_THRESHOLD = 0.5
DEFAULT_EXPORT_PATH = Path("data/chembl_modeling.csv")
DEFAULT_REPORTS_DIR = Path("exploration/reports")
RDLogger.DisableLog("rdApp.warning")
MORGAN_GENERATOR_RADIUS2 = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
MORGAN_GENERATOR_RADIUS3 = rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=2048)

FEATURE_SET_CANDIDATES = {
    "rdkit_fingerprint": [
        "morgan_tanimoto_radius2",
        "morgan_dice_radius2",
        "morgan_tanimoto_radius3",
        "rdkit_fp_tanimoto",
        "maccs_tanimoto",
        "mol_weight_a",
        "mol_weight_b",
        "mol_weight_abs_delta",
        "tpsa_a",
        "tpsa_b",
        "tpsa_abs_delta",
        "logp_a",
        "logp_b",
        "logp_abs_delta",
        "h_donor_a",
        "h_donor_b",
        "h_donor_abs_delta",
        "h_acceptor_a",
        "h_acceptor_b",
        "h_acceptor_abs_delta",
        "rot_bond_a",
        "rot_bond_b",
        "rot_bond_abs_delta",
        "ring_count_a",
        "ring_count_b",
        "ring_count_abs_delta",
        "fraction_csp3_a",
        "fraction_csp3_b",
        "fraction_csp3_abs_delta",
    ],
    "structure_proxy": [
        "smiles_length_a",
        "smiles_length_b",
        "smiles_length_abs_delta",
        "atom_token_count_a",
        "atom_token_count_b",
        "atom_token_count_abs_delta",
        "hetero_count_a",
        "hetero_count_b",
        "hetero_count_abs_delta",
        "ring_marker_count_a",
        "ring_marker_count_b",
        "ring_marker_count_abs_delta",
        "halogen_count_a",
        "halogen_count_b",
        "halogen_count_abs_delta",
    ],
    "structure_enriched": [
        "morgan_tanimoto_radius2",
        "morgan_dice_radius2",
        "morgan_tanimoto_radius3",
        "rdkit_fp_tanimoto",
        "maccs_tanimoto",
        "char_bigram_jaccard",
        "char_trigram_jaccard",
        "atom_token_jaccard",
        "atom_bigram_jaccard",
        "smiles_length_a",
        "smiles_length_b",
        "smiles_length_abs_delta",
        "atom_token_count_a",
        "atom_token_count_b",
        "atom_token_count_abs_delta",
        "hetero_count_a",
        "hetero_count_b",
        "hetero_count_abs_delta",
        "ring_marker_count_a",
        "ring_marker_count_b",
        "ring_marker_count_abs_delta",
        "halogen_count_a",
        "halogen_count_b",
        "halogen_count_abs_delta",
        "aromatic_atom_count_a",
        "aromatic_atom_count_b",
        "aromatic_atom_count_abs_delta",
        "branch_count_a",
        "branch_count_b",
        "branch_count_abs_delta",
        "bond_order_count_a",
        "bond_order_count_b",
        "bond_order_count_abs_delta",
        "stereo_marker_count_a",
        "stereo_marker_count_b",
        "stereo_marker_count_abs_delta",
        "bracket_atom_count_a",
        "bracket_atom_count_b",
        "bracket_atom_count_abs_delta",
        "atom_diversity_a",
        "atom_diversity_b",
        "atom_diversity_abs_delta",
        "hetero_ratio_a",
        "hetero_ratio_b",
        "hetero_ratio_abs_delta",
        "aromatic_ratio_a",
        "aromatic_ratio_b",
        "aromatic_ratio_abs_delta",
        "mol_weight_a",
        "mol_weight_b",
        "mol_weight_abs_delta",
        "tpsa_a",
        "tpsa_b",
        "tpsa_abs_delta",
        "logp_a",
        "logp_b",
        "logp_abs_delta",
        "h_donor_a",
        "h_donor_b",
        "h_donor_abs_delta",
        "h_acceptor_a",
        "h_acceptor_b",
        "h_acceptor_abs_delta",
        "rot_bond_a",
        "rot_bond_b",
        "rot_bond_abs_delta",
        "ring_count_a",
        "ring_count_b",
        "ring_count_abs_delta",
        "fraction_csp3_a",
        "fraction_csp3_b",
        "fraction_csp3_abs_delta",
    ],
    "structure_plus_context": [
        "morgan_tanimoto_radius2",
        "morgan_dice_radius2",
        "morgan_tanimoto_radius3",
        "rdkit_fp_tanimoto",
        "maccs_tanimoto",
        "char_bigram_jaccard",
        "char_trigram_jaccard",
        "atom_token_jaccard",
        "atom_bigram_jaccard",
        "smiles_length_a",
        "smiles_length_b",
        "smiles_length_abs_delta",
        "atom_token_count_a",
        "atom_token_count_b",
        "atom_token_count_abs_delta",
        "hetero_count_a",
        "hetero_count_b",
        "hetero_count_abs_delta",
        "ring_marker_count_a",
        "ring_marker_count_b",
        "ring_marker_count_abs_delta",
        "halogen_count_a",
        "halogen_count_b",
        "halogen_count_abs_delta",
        "aromatic_atom_count_a",
        "aromatic_atom_count_b",
        "aromatic_atom_count_abs_delta",
        "branch_count_a",
        "branch_count_b",
        "branch_count_abs_delta",
        "bond_order_count_a",
        "bond_order_count_b",
        "bond_order_count_abs_delta",
        "stereo_marker_count_a",
        "stereo_marker_count_b",
        "stereo_marker_count_abs_delta",
        "bracket_atom_count_a",
        "bracket_atom_count_b",
        "bracket_atom_count_abs_delta",
        "atom_diversity_a",
        "atom_diversity_b",
        "atom_diversity_abs_delta",
        "hetero_ratio_a",
        "hetero_ratio_b",
        "hetero_ratio_abs_delta",
        "aromatic_ratio_a",
        "aromatic_ratio_b",
        "aromatic_ratio_abs_delta",
        "mol_weight_a",
        "mol_weight_b",
        "mol_weight_abs_delta",
        "tpsa_a",
        "tpsa_b",
        "tpsa_abs_delta",
        "logp_a",
        "logp_b",
        "logp_abs_delta",
        "h_donor_a",
        "h_donor_b",
        "h_donor_abs_delta",
        "h_acceptor_a",
        "h_acceptor_b",
        "h_acceptor_abs_delta",
        "rot_bond_a",
        "rot_bond_b",
        "rot_bond_abs_delta",
        "ring_count_a",
        "ring_count_b",
        "ring_count_abs_delta",
        "fraction_csp3_a",
        "fraction_csp3_b",
        "fraction_csp3_abs_delta",
    ],
}
L2_CANDIDATES = [0.01, 0.1, 0.5]
THRESHOLD_CANDIDATES = [0.45, 0.5, 0.55, 0.6]


def compute_numeric_stats(
    rows: list[dict[str, object]], numeric_feature_names: list[str]
) -> dict[str, tuple[float, float]]:
    stats: dict[str, tuple[float, float]] = {}
    for feature_name in numeric_feature_names:
        values = [float(row.get(feature_name, 0.0)) for row in rows]
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        std_value = math.sqrt(variance)
        stats[feature_name] = (mean_value, std_value if std_value > 0 else 1.0)
    return stats


def vectorize_row(
    row: dict[str, object],
    numeric_feature_names: list[str],
    categorical_feature_names: list[str],
    numeric_stats: dict[str, tuple[float, float]],
) -> list[float]:
    values: list[float] = []
    for feature_name in numeric_feature_names:
        mean_value, std_value = numeric_stats[feature_name]
        numeric_value = float(row.get(feature_name, 0.0))
        values.append((numeric_value - mean_value) / std_value)
    for feature_name in categorical_feature_names:
        key, expected = feature_name.split("=", maxsplit=1)
        values.append(1.0 if str(row[key]) == expected else 0.0)
    return values


def evaluate_probabilities(
    targets: list[int], probabilities: list[float], threshold: float = DEFAULT_THRESHOLD
) -> dict[str, object]:
    brier = sum(
        (float(target) - probability) ** 2
        for target, probability in zip(targets, probabilities, strict=True)
    ) / len(targets)
    log_loss = 0.0
    for target, probability in zip(targets, probabilities, strict=True):
        clipped_probability = min(max(probability, 1e-9), 1 - 1e-9)
        log_loss += -(
            float(target) * math.log(clipped_probability)
            + (1.0 - float(target)) * math.log(1.0 - clipped_probability)
        )
    log_loss /= len(targets)

    binary_predictions = [1 if probability >= threshold else 0 for probability in probabilities]
    true_positive = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 1 and prediction == 1
    )
    true_negative = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 0 and prediction == 0
    )
    false_positive = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 0 and prediction == 1
    )
    false_negative = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 1 and prediction == 0
    )
    accuracy = (true_positive + true_negative) / len(targets)
    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive)
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative)
        else 0.0
    )
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "sample_count": len(targets),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {
            "tp": true_positive,
            "tn": true_negative,
            "fp": false_positive,
            "fn": false_negative,
        },
        "brier_score": round(brier, 4),
        "log_loss": round(log_loss, 4),
    }


def load_rows(path: Path) -> list[dict[str, object]]:
    with path.open() as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, object]] = []
        for row in reader:
            smiles_a = row["smiles_a"]
            smiles_b = row["smiles_b"]
            features_a = _extract_smiles_features(smiles_a)
            features_b = _extract_smiles_features(smiles_b)
            pair_features = _pairwise_smiles_features(smiles_a, smiles_b)
            rdkit_features_a = _rdkit_descriptor_features(smiles_a)
            rdkit_features_b = _rdkit_descriptor_features(smiles_b)
            rdkit_pair_features = _rdkit_pairwise_features(smiles_a, smiles_b)
            rows.append(
                {
                    **row,
                    "is_similar": int(row["is_similar"]),
                    "similarity_score": float(row["similarity_score"]),
                    "activity_delta": float(row["activity_delta"]),
                    "activity_value_a": float(row["activity_value_a"]),
                    "activity_value_b": float(row["activity_value_b"]),
                    "activity_value_mean": float(row["activity_value_mean"]),
                    "smiles_length_a": float(row["smiles_length_a"]),
                    "smiles_length_b": float(row["smiles_length_b"]),
                    "smiles_length_abs_delta": float(row["smiles_length_abs_delta"]),
                    **pair_features,
                    **_pair_feature_values(features_a, features_b),
                    **_pair_feature_values(rdkit_features_a, rdkit_features_b),
                    **rdkit_pair_features,
                }
            )
        return rows


def _pair_feature_values(
    features_a: dict[str, float], features_b: dict[str, float]
) -> dict[str, float]:
    paired: dict[str, float] = {}
    for feature_name, value_a in features_a.items():
        value_b = features_b[feature_name]
        paired[f"{feature_name}_a"] = float(value_a)
        paired[f"{feature_name}_b"] = float(value_b)
        paired[f"{feature_name}_abs_delta"] = float(abs(value_a - value_b))
    return paired


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _extract_smiles_features(smiles: str) -> dict[str, float]:
    atom_token_count = _atom_token_count(smiles)
    hetero_count = _hetero_count(smiles)
    aromatic_atom_count = _aromatic_atom_count(smiles)
    return {
        "atom_token_count": float(atom_token_count),
        "hetero_count": float(hetero_count),
        "ring_marker_count": float(_ring_marker_count(smiles)),
        "halogen_count": float(_halogen_count(smiles)),
        "aromatic_atom_count": float(aromatic_atom_count),
        "branch_count": float(smiles.count("(")),
        "bond_order_count": float(smiles.count("=") + smiles.count("#")),
        "stereo_marker_count": float(smiles.count("@")),
        "bracket_atom_count": float(smiles.count("[")),
        "atom_diversity": float(_atom_diversity(smiles)),
        "hetero_ratio": float(_safe_ratio(hetero_count, atom_token_count)),
        "aromatic_ratio": float(_safe_ratio(aromatic_atom_count, atom_token_count)),
    }


def _pairwise_smiles_features(smiles_a: str, smiles_b: str) -> dict[str, float]:
    atom_tokens_a = _atom_tokens(smiles_a)
    atom_tokens_b = _atom_tokens(smiles_b)
    return {
        "char_bigram_jaccard": float(
            _jaccard_similarity(_char_ngrams(smiles_a, 2), _char_ngrams(smiles_b, 2))
        ),
        "char_trigram_jaccard": float(
            _jaccard_similarity(_char_ngrams(smiles_a, 3), _char_ngrams(smiles_b, 3))
        ),
        "atom_token_jaccard": float(_jaccard_similarity(set(atom_tokens_a), set(atom_tokens_b))),
        "atom_bigram_jaccard": float(
            _jaccard_similarity(_token_ngrams(atom_tokens_a, 2), _token_ngrams(atom_tokens_b, 2))
        ),
    }


def _rdkit_descriptor_features(smiles: str) -> dict[str, float]:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return {
            "mol_weight": 0.0,
            "tpsa": 0.0,
            "logp": 0.0,
            "h_donor": 0.0,
            "h_acceptor": 0.0,
            "rot_bond": 0.0,
            "ring_count": 0.0,
            "fraction_csp3": 0.0,
        }
    return {
        "mol_weight": float(Descriptors.MolWt(molecule)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(molecule)),
        "logp": float(Descriptors.MolLogP(molecule)),
        "h_donor": float(rdMolDescriptors.CalcNumHBD(molecule)),
        "h_acceptor": float(rdMolDescriptors.CalcNumHBA(molecule)),
        "rot_bond": float(rdMolDescriptors.CalcNumRotatableBonds(molecule)),
        "ring_count": float(rdMolDescriptors.CalcNumRings(molecule)),
        "fraction_csp3": float(rdMolDescriptors.CalcFractionCSP3(molecule)),
    }


def _rdkit_pairwise_features(smiles_a: str, smiles_b: str) -> dict[str, float]:
    molecule_a = Chem.MolFromSmiles(smiles_a)
    molecule_b = Chem.MolFromSmiles(smiles_b)
    if molecule_a is None or molecule_b is None:
        return {
            "morgan_tanimoto_radius2": 0.0,
            "morgan_dice_radius2": 0.0,
            "morgan_tanimoto_radius3": 0.0,
            "rdkit_fp_tanimoto": 0.0,
            "maccs_tanimoto": 0.0,
        }

    morgan_a_r2 = MORGAN_GENERATOR_RADIUS2.GetFingerprint(molecule_a)
    morgan_b_r2 = MORGAN_GENERATOR_RADIUS2.GetFingerprint(molecule_b)
    morgan_a_r3 = MORGAN_GENERATOR_RADIUS3.GetFingerprint(molecule_a)
    morgan_b_r3 = MORGAN_GENERATOR_RADIUS3.GetFingerprint(molecule_b)
    rdkit_fp_a = Chem.RDKFingerprint(molecule_a)
    rdkit_fp_b = Chem.RDKFingerprint(molecule_b)
    maccs_a = MACCSkeys.GenMACCSKeys(molecule_a)
    maccs_b = MACCSkeys.GenMACCSKeys(molecule_b)

    return {
        "morgan_tanimoto_radius2": float(DataStructs.TanimotoSimilarity(morgan_a_r2, morgan_b_r2)),
        "morgan_dice_radius2": float(DataStructs.DiceSimilarity(morgan_a_r2, morgan_b_r2)),
        "morgan_tanimoto_radius3": float(DataStructs.TanimotoSimilarity(morgan_a_r3, morgan_b_r3)),
        "rdkit_fp_tanimoto": float(DataStructs.TanimotoSimilarity(rdkit_fp_a, rdkit_fp_b)),
        "maccs_tanimoto": float(DataStructs.TanimotoSimilarity(maccs_a, maccs_b)),
    }


def _atom_token_count(smiles: str) -> int:
    return len(_atom_tokens(smiles))


def _atom_tokens(smiles: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(smiles):
        token = smiles[index : index + 2]
        if token in {"Cl", "Br"}:
            tokens.append(token)
            index += 2
            continue
        character = smiles[index]
        if character.isalpha() and (
            character.isupper() or character in {"c", "n", "o", "s", "p"}
        ):
            tokens.append(character)
        index += 1
    return tokens


def _hetero_count(smiles: str) -> int:
    count = 0
    index = 0
    while index < len(smiles):
        token = smiles[index : index + 2]
        if token in {"Cl", "Br"}:
            count += 1
            index += 2
            continue
        if smiles[index] in {"N", "O", "S", "P", "F", "I"}:
            count += 1
        index += 1
    return count


def _ring_marker_count(smiles: str) -> int:
    return sum(1 for character in smiles if character.isdigit())


def _halogen_count(smiles: str) -> int:
    return smiles.count("F") + smiles.count("Cl") + smiles.count("Br") + smiles.count("I")


def _aromatic_atom_count(smiles: str) -> int:
    return sum(1 for character in smiles if character in {"c", "n", "o", "s", "p"})


def _atom_diversity(smiles: str) -> int:
    return len(set(_atom_tokens(smiles)))


def _char_ngrams(smiles: str, n: int) -> set[str]:
    if len(smiles) < n:
        return {smiles} if smiles else set()
    return {smiles[index : index + n] for index in range(len(smiles) - n + 1)}


def _token_ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


def _jaccard_similarity(left: set[object], right: set[object]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def split_rows(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    result = {"train": [], "val": [], "test": []}
    for row in rows:
        result[str(row["split"])].append(row)
    return result


def categorical_feature_names(rows: list[dict[str, object]]) -> list[str]:
    names = []
    names.extend(
        f"target_name={name}" for name in sorted({str(row["target_name"]) for row in rows})
    )
    names.extend(
        f"standard_type={name}" for name in sorted({str(row["standard_type"]) for row in rows})
    )
    return names


def choose_best_configuration(rows: list[dict[str, object]]) -> dict[str, object]:
    split_to_rows = split_rows(rows)
    train_rows = split_to_rows["train"]
    val_rows = split_to_rows["val"]
    category_names = categorical_feature_names(rows)
    candidates: list[dict[str, object]] = []

    for feature_set_name, numeric_feature_names in FEATURE_SET_CANDIDATES.items():
        for use_categories in (False, True):
            active_categories = category_names if use_categories else []
            numeric_stats = compute_numeric_stats(train_rows, numeric_feature_names)
            train_features = [
                vectorize_row(row, numeric_feature_names, active_categories, numeric_stats)
                for row in train_rows
            ]
            val_features = [
                vectorize_row(row, numeric_feature_names, active_categories, numeric_stats)
                for row in val_rows
            ]
            train_targets = [int(row["is_similar"]) for row in train_rows]
            val_targets = [int(row["is_similar"]) for row in val_rows]
            for l2_penalty in L2_CANDIDATES:
                model = LogisticRegression(C=1.0 / l2_penalty, max_iter=1000, random_state=42)
                model.fit(train_features, train_targets)
                val_probabilities = [
                    float(probability) for probability in model.predict_proba(val_features)[:, 1]
                ]
                for threshold in THRESHOLD_CANDIDATES:
                    metrics = evaluate_probabilities(val_targets, val_probabilities, threshold=threshold)
                    candidates.append(
                        {
                            "feature_set_name": feature_set_name,
                            "numeric_feature_names": numeric_feature_names,
                            "categorical_feature_names": active_categories,
                            "use_categories": use_categories,
                            "l2_penalty": l2_penalty,
                            "threshold": threshold,
                            "metrics": metrics,
                        }
                    )

    candidates.sort(
        key=lambda candidate: (
            float(candidate["metrics"]["f1"]),
            float(candidate["metrics"]["accuracy"]),
            -float(candidate["metrics"]["log_loss"]),
        ),
        reverse=True,
    )
    return candidates[0]


def build_report(export_path: Path) -> dict[str, object]:
    rows = load_rows(export_path)
    split_to_rows = split_rows(rows)
    selected = choose_best_configuration(rows)
    numeric_feature_names = list(selected["numeric_feature_names"])
    category_names = list(selected["categorical_feature_names"])
    numeric_stats = compute_numeric_stats(
        split_to_rows["train"] + split_to_rows["val"], numeric_feature_names
    )
    development_rows = split_to_rows["train"] + split_to_rows["val"]
    development_features = [
        vectorize_row(row, numeric_feature_names, category_names, numeric_stats)
        for row in development_rows
    ]
    test_features = [
        vectorize_row(row, numeric_feature_names, category_names, numeric_stats)
        for row in split_to_rows["test"]
    ]
    development_targets = [int(row["is_similar"]) for row in development_rows]
    test_targets = [int(row["is_similar"]) for row in split_to_rows["test"]]
    model = LogisticRegression(
        C=1.0 / float(selected["l2_penalty"]), max_iter=1000, random_state=42
    )
    model.fit(development_features, development_targets)
    development_probabilities = [
        float(probability) for probability in model.predict_proba(development_features)[:, 1]
    ]
    test_probabilities = [
        float(probability) for probability in model.predict_proba(test_features)[:, 1]
    ]
    return {
        "configuration": {
            "export_path": str(export_path),
            "label_threshold": DEFAULT_THRESHOLD,
            "selected_feature_set": selected["feature_set_name"],
            "selected_l2_penalty": selected["l2_penalty"],
            "selected_probability_threshold": selected["threshold"],
            "selected_use_categories": selected["use_categories"],
            "numeric_features": numeric_feature_names,
            "categorical_features": category_names,
        },
        "dataset": {
            "row_count": len(rows),
            "split_counts": {key: len(value) for key, value in split_to_rows.items()},
            "label_balance": {
                "similar": sum(int(row["is_similar"]) for row in rows),
                "dissimilar": sum(1 - int(row["is_similar"]) for row in rows),
            },
        },
        "model_selection": {
            "candidate_feature_sets": list(FEATURE_SET_CANDIDATES),
            "candidate_l2_penalties": L2_CANDIDATES,
            "candidate_thresholds": THRESHOLD_CANDIDATES,
            "selected_configuration": {
                "feature_set_name": selected["feature_set_name"],
                "threshold": selected["threshold"],
                "l2_penalty": selected["l2_penalty"],
                "use_categories": selected["use_categories"],
                "validation_metrics": selected["metrics"],
            },
        },
        "model": {
            "name": "sql_activity_pair_logistic_classifier",
            "metrics": {
                "development": evaluate_probabilities(
                    development_targets,
                    development_probabilities,
                    threshold=float(selected["threshold"]),
                ),
                "test": evaluate_probabilities(
                    test_targets,
                    test_probabilities,
                    threshold=float(selected["threshold"]),
                ),
            },
            "coefficients": {
                "bias": round(float(model.intercept_[0]), 6),
                "weights": {
                    feature_name: round(float(weight), 6)
                    for feature_name, weight in zip(
                        numeric_feature_names + category_names,
                        model.coef_[0],
                        strict=True,
                    )
                },
            },
        },
        "test_examples": [
            {
                "pair_id": row["pair_id"],
                "target_name": row["target_name"],
                "standard_type": row["standard_type"],
                "similarity_score": round(float(row["similarity_score"]), 4),
                "activity_delta": round(float(row["activity_delta"]), 4),
                "actual_label": int(row["is_similar"]),
                "predicted_probability": round(probability, 4),
                "predicted_label": int(probability >= float(selected["threshold"])),
            }
            for row, probability in zip(
                split_to_rows["test"][:20], test_probabilities[:20], strict=True
            )
        ],
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# SQL Activity Pair Model",
        "",
        f"- Export path: {report['configuration']['export_path']}",
        f"- Selected feature set: {report['configuration']['selected_feature_set']}",
        (
            "- Selected probability threshold: "
            f"{report['configuration']['selected_probability_threshold']}"
        ),
        f"- Selected L2 penalty: {report['configuration']['selected_l2_penalty']}",
        f"- Rows: {report['dataset']['row_count']}",
        (
            "- Split counts: "
            + ", ".join(
                f"{name}={count}" for name, count in report["dataset"]["split_counts"].items()
            )
        ),
        (
            "- Label balance: "
            f"similar={report['dataset']['label_balance']['similar']}, "
            f"dissimilar={report['dataset']['label_balance']['dissimilar']}"
        ),
        "",
        "## Validation Selection",
        "",
        (
            "- Validation metrics: "
            f"accuracy={report['model_selection']['selected_configuration']['validation_metrics']['accuracy']}, "
            f"f1={report['model_selection']['selected_configuration']['validation_metrics']['f1']}, "
            f"log_loss={report['model_selection']['selected_configuration']['validation_metrics']['log_loss']}"
        ),
        "",
        "## Classification Metrics",
        "",
        "| split | log_loss | brier | accuracy | precision | recall | f1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split_name in ("development", "test"):
        metrics = report["model"]["metrics"][split_name]
        lines.append(
            f"| {split_name} | {metrics['log_loss']} | {metrics['brier_score']} | "
            f"{metrics['accuracy']} | {metrics['precision']} | {metrics['recall']} | {metrics['f1']} |"
        )
    lines.extend(
        [
            "",
            "## Test Predictions",
            "",
            "| pair_id | target | type | similarity_score | activity_delta | actual_label | probability | predicted_label |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for example in report["test_examples"]:
        lines.append(
            "| {pair_id} | {target_name} | {standard_type} | {similarity_score} | "
            "{activity_delta} | {actual_label} | {predicted_probability} | {predicted_label} |".format(
                **example
            )
        )
    return "\n".join(lines) + "\n"


def write_report(
    report: dict[str, object], reports_dir: Path = DEFAULT_REPORTS_DIR
) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "sql_activity_pair_model.json"
    markdown_path = reports_dir / "sql_activity_pair_model.md"
    json_path.write_text(json.dumps(report, indent=2))
    markdown_path.write_text(render_markdown(report))
    return json_path, markdown_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and report the SQL-backed activity pair classifier."
    )
    parser.add_argument(
        "export_path",
        nargs="?",
        default=str(DEFAULT_EXPORT_PATH),
        help=f"Modeling CSV exported from the SQL ETL pipeline (default: {DEFAULT_EXPORT_PATH})",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(DEFAULT_REPORTS_DIR),
        help=f"Directory for JSON/Markdown reports (default: {DEFAULT_REPORTS_DIR})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    export_path = Path(args.export_path).expanduser().resolve()
    reports_dir = Path(args.reports_dir).expanduser().resolve()
    report = build_report(export_path)
    json_path, markdown_path = write_report(report, reports_dir=reports_dir)
    test_metrics = report["model"]["metrics"]["test"]
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(f"Test accuracy: {test_metrics['accuracy']}")
    print(f"Test f1: {test_metrics['f1']}")
    print(f"Test log loss: {test_metrics['log_loss']}")
    return 0
