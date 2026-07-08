# import argparse

# from email import parser
import pandas as pd
from pathlib import Path
from utils import round_amount, clean_amount



def main(
    # input_dir: str,
    # output_dir: str,
    # contribution_start: str,
    # contribution_end: str,
    # newsroom: str,
    file_format="csv",
):
    # parser = argparse.ArgumentParser()

    # parser.add_argument("input_dir")
    # parser.add_argument("output_dir")
    # parser.add_argument("contribution_start")
    # parser.add_argument("contribution_end")
    # parser.add_argument("newsroom")
    # parser.add_argument("file_format")

    input_dir = Path("raw_contributions")
    output_dir = Path("data_output")
    candidate_info_dir = Path("candidate_info/candidate_info.tsv")
    contribution_start = "2020-01-01"
    contribution_end = "2026-07-06"
    newsroom = "Slice of Culture"
    pull_date = "2026-07-06"
    state = "NJ"

    file_names = input_dir.glob(f"*{file_format}")

    df_list = []

    # read in all files into one list
    for f in file_names:
        temp_df = pd.read_csv(f, index_col=False)

        df_list += [temp_df]

    df = pd.concat(df_list, ignore_index=True)
    # Rename the candidate and Amount columns for clarity
    df.rename(columns={"EntityName": "Candidate", "ContributionAmount":"Amount"}, inplace=True)

    # ----------------------------------------------
    # LOAD IN CANDIDATE INFO
    # ----------------------------------------------

    cand_info = pd.read_csv(
        candidate_info_dir,
        sep="\t",
        usecols=["Name", "Office/Cmte", "Party", "Election Type"],
    ).rename(
        columns={
            "Name": "Candidate",
            "Office/Cmte": "Office",
            "Election Type": "Election",
        }
    ).drop_duplicates(["Candidate"]).sort_values(["Office", "Candidate"]).reset_index(drop=True)

    # Add in ID column
    cand_info["CandidateID"] = list(range(1, len(cand_info["Candidate"]) + 1))

    df = pd.merge(df, cand_info, on="Candidate", how="left")

    # ----------------------------------------------
    # ADD EXTRA COLUMNS, CLEAN STRINGS
    # ----------------------------------------------

    df["State"] = "New Jersey"
    df["PullDate"] = (
        pull_date  # hard-coded for now, as all data was pulled the same day
    )


    # Clean up the values for candidates, individuals, location, etc.
    title_cols = [
        "Candidate",
        "Location",
        "Office",
        "FirstName",
        "LastName",
        "NonIndName",
        "Party",
        "Election",
        "ContributorType",
    ]
    df.loc[:, title_cols] = df.loc[:, title_cols].apply(lambda x: x.str.strip().str.title())

    # Covert to datetime and filter
    df["ContributionDate"] = pd.to_datetime(df["ContributionDate"], errors="coerce")
    df = df[
        (df["ContributionDate"] >= contribution_start)
        & (df["ContributionDate"] <= contribution_end)
    ].reset_index(drop=True)

    df["Amount"] = clean_amount(df["Amount"])

    # ----------------------------------------------
    # FIX CONTRIBUTOR TYPES and NAME
    # ----------------------------------------------

    # fills blank contribution type with Unknown, set Pac to PAC
    df["ContributorType"] = (
        df["ContributorType"]
        .replace(r"^\s*$", pd.NA, regex=True)
        .replace("Not Provided", pd.NA)
        .fillna("(Unknown)")
        .str.replace("Pac", "PAC")
    )
    df.rename(columns={"ContributorType":"Contributor Type"}, inplace=True)

    # clean contributor name - combine first name/last name for individuals 
    # and NonIndName for companies
    df.loc[df["IsIndividual"]=="Y","ContributorName"] = (
        df.loc[df["IsIndividual"]=="Y","FirstName"].fillna("")+
        " "+
        df.loc[df["IsIndividual"]=="Y","LastName"].fillna("")
    )
    df.loc[df["IsIndividual"]=="N","ContributorName"] = (
        df.loc[df["IsIndividual"]=="N","NonIndName"].fillna("")
        # make LLC and LLPs uppercase
        .str.replace("Llp", "LLP")
        .str.replace("Llc", "LLC")
        # fix PAC name
        .str.replace("Pac", "PAC")
    )

    # ----------------------------------------------
    # SUMMARIZE DATA
    # ----------------------------------------------

    # total contributions
    summary = (
        df.groupby(
            ["CandidateID", "Candidate", "Location", "Office"], dropna=False
        ).agg(**{"Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum")})
    ).reset_index(drop=False)
    summary["Total Contributions"] = round_amount(summary["Total Contributions"])


    # contributor type
    contrib_summary = (
        df.groupby(["CandidateID", "Candidate", "Contributor Type"], dropna=False).agg(
            **{
                "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum"),
                "Number of Contributions": pd.NamedAgg(
                    column="Amount", aggfunc="count"
                ),
            }
        )
    ).reset_index(drop=False)

    contrib_summary["Total Contributions"] = round_amount(
        contrib_summary["Total Contributions"]
    )

    # top contributors grouped by cleaned name and cleaned city
    donor_summary = (
        df.groupby(
            [
                "CandidateID",
                "Candidate",
                "ContributorName",
            ],
            dropna=False,
        )
        .agg(
            **{
                "Contributor Type": pd.NamedAgg(
                    column="Contributor Type",
                    aggfunc=lambda x: " | ".join(
                        pd.Series(x.dropna().astype(str).unique()).sort_values()
                    ),
                ),
                "Contributor Name": pd.NamedAgg(
                    column="ContributorName",
                    aggfunc=lambda x: " | ".join(
                        pd.Series(x.dropna().astype(str).unique()).sort_values()
                    ),
                ),
                "Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum"),
                "Number of Contributions": pd.NamedAgg(
                    column="Amount", aggfunc="count"
                ),
            }
        )
        .sort_values(
            ["Total Contributions", "Contributor Name"], ascending=False
        )  # sort by amount and name to keep top 10 list stable
        .groupby(["CandidateID", "Candidate"], group_keys=False)
        .apply(lambda g: g.nlargest(10, "Total Contributions"))
        .reset_index(drop=False)
        .drop(columns=["Contributor Name"])
    )

    donor_summary["Total Contributions"] = round_amount(
        donor_summary["Total Contributions"]
    )

    # pac contributors
    pacs = df[
        df["Contributor Type"]
        .str.strip()
        .str.lower()
        .str.contains("pac|political action committee")
    ]
    pacs_summary = (
        pacs.groupby(["CandidateID", "Candidate", "ContributorName"])
        .agg(**{"Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum")})
        .groupby(["CandidateID", "Candidate"], group_keys=False)
        # sort by amount and name to keep list stable
        .apply(
            lambda x: x.sort_values(
                ["Total Contributions", "ContributorName"], ascending=False
            )
        )
    ).reset_index(drop=False)

    pacs_summary["Total Contributions"] = round_amount(
        pacs_summary["Total Contributions"]
    )

    # corporate contributors
    corporates = df[
        df["Contributor Type"]
        .str.strip()
        .str.lower()
        .str.contains("business/corp")
    ]
    corporates_summary = (
        corporates.groupby(["CandidateID", "Candidate", "ContributorName"])
        .agg(**{"Total Contributions": pd.NamedAgg(column="Amount", aggfunc="sum")})
        .groupby(["CandidateID", "Candidate"], group_keys=False)
        .apply(
            lambda x: x.sort_values(
                ["Total Contributions", "ContributorName"], ascending=False
            )
        )
    ).reset_index(drop=False)

    corporates_summary["Total Contributions"] = round_amount(
        corporates_summary["Total Contributions"]
    )


    # parmeters to show on UI
    parameters = pd.DataFrame(
        {
            "Newsroom": newsroom,
            "State": state.upper(),
            "Data Start": contribution_start,
            "Data End": contribution_end,
        },
        index=[0],
    )

    # export csvs
    summary.to_csv(output_dir / "total_contributions.csv", index=False)
    contrib_summary.to_csv(output_dir / "contributor_types.csv", index=False)
    donor_summary.to_csv(output_dir / "top_contributors.csv", index=False)
    pacs_summary.to_csv(output_dir / "pac_contributors.csv", index=False)
    corporates_summary.to_csv(
        output_dir / "corporate_contributors.csv", index=False
    )
    parameters.to_csv(output_dir / "parameters.csv", index=False)

    # no address, so no state-grouped contributions
    # instate_contr.to_csv(output_dir + "/" + "instate_perc.csv", index=False)
    # state_contr.to_csv(output_dir + "/" + "all_state_perc.csv", index=False)


# donor_summary.to_csv("donors_over_3000_summary.csv", index=False)
# contrib_summary.to_csv("contributor_type_summary.csv")


if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument(
    #    "input_dir","output_dir", "contribution_start", "contribution_end","file_formet",
    #    help="Input CSV file, e.g. Contributions_anthony_merante.csv"
    # )
    # parser = argparse.ArgumentParser()

    # parser.add_argument("input_dir")
    # parser.add_argument("output_dir")
    # parser.add_argument("contribution_start")
    # parser.add_argument("contribution_end")
    # parser.add_argument("newsroom")
    # parser.add_argument("file_format", nargs="?", default="csv")

    # args = parser.parse_args()

    main(
        # args.input_dir,
        # args.output_dir,
        # args.contribution_start,
        # args.contribution_end,
        # args.newsroom,
        # args.file_format,
    )
