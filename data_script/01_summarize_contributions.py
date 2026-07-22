import pandas as pd
from pathlib import Path
from utils import round_amount, clean_amount



def main(file_format="csv",):

    ############# CONFIG ##########################
    county = "HUDSON COUNTY"
    contribution_start = "2020-01-01"
    newsroom = "Slice of Culture"
    pull_date = "2026-07-21"
    contribution_end = pull_date
    state = "NJ"
    ###############################################

    input_dir = Path(f"raw_contributions/{county}")
    output_dir = Path(f"data_output/{county}")
    candidate_info_dir = input_dir / Path(f"candidates_{'_'.join(county.split(' '))}_2026.csv")
    file_names = input_dir.glob(f"*{file_format}")

    df_list = []

    # read in all files into one list
    for f in file_names:
        # read all files not including candidate info
        if "candidates_" not in str(f):
            try:
                temp_df = pd.read_csv(f, index_col=False)
                # Save EID from name of the file
                temp_df["CandidateID"] = int(str(f).split("_contribution_detail")[0].split("_")[-1])
                df_list += [temp_df]
            except Exception as e:
                # Most of these are issues with commas in names
                # TODO fix the scraping code to remove these
                raise ValueError(e)

    df = pd.concat(df_list, ignore_index=True)
    # Rename the candidate and Amount columns for clarity
    df.rename(columns={"EntityName": "Candidate", "ContributionAmount":"Amount"}, inplace=True)

    # ----------------------------------------------
    # LOAD IN CANDIDATE INFO
    # ----------------------------------------------

    cand_info = pd.read_csv(
        candidate_info_dir
    ).rename(
        columns={
            "name": "Candidate",
            "office_cmte": "Office",
            "election_type": "Election",
            "eid":"CandidateID",
            "party": "Party",
        }
    ).drop_duplicates(["Candidate"]).sort_values(["Office", "Candidate"]).reset_index(drop=True)

    # There are multiple rows for the same candidate based on primary vs full election
    df = pd.merge(df, cand_info, on=["CandidateID", "Candidate"], how="left")

    # ----------------------------------------------
    # ADD EXTRA COLUMNS, CLEAN STRINGS
    # ----------------------------------------------

    df["State"] = "New Jersey"
    # hard-coded for now, as all data was pulled the same day
    df["PullDate"] = pull_date


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
    output_dir.mkdir(exist_ok=True)

    summary.to_csv(output_dir / "total_contributions.csv", index=False)
    contrib_summary.to_csv(output_dir / "contributor_types.csv", index=False)
    donor_summary.to_csv(output_dir / "top_contributors.csv", index=False)
    pacs_summary.to_csv(output_dir / "pac_contributors.csv", index=False)
    corporates_summary.to_csv(
        output_dir / "corporate_contributors.csv", index=False
    )
    parameters.to_csv(output_dir / "parameters.csv", index=False)


if __name__ == "__main__":
    main()
