import React from 'react';
import axios from 'axios';
import getCookie from '../auth/Cookie';
var csrftoken = getCookie('csrftoken');


const Pagination = ({ api_url, state, setState }) => {
    const previousList = () => {
        const previous = state.previous
        if (previous !== null && 0 !== state.page_active) {
            axios({
                method: 'get',
                url: previous,
                headers: {
                    'Authorization': localStorage.auth_token,
                    'X-CSRFToken': csrftoken
                },
            })
                .then(function (response) {
                    setState(oldstate => {
                        let response_data = response.data
                        let paginated_results = {
                            ...oldstate,
                            next: response_data.next,
                            previous: response_data.previous,
                            count: response_data.count,
                            page_active: ((response_data.page_active - 1) <= 1 ? 1 : Number(response_data.page_active) - 1),
                            num_pages: response_data.num_pages,
                            data: response_data.data,
                            headers: [],
                            url: api_url,
                            limit: 5,
                            explore_type: "all"

                        };
                        return paginated_results
                    });

                })
        }
    };
    const nextList = () => {
        const next = state.next
        if (next !== null && state.count !== state.page_active) {
            axios({
                method: 'get',
                url: next,
                headers: {
                    'Authorization': localStorage.auth_token,
                    'X-CSRFToken': csrftoken
                },
            })
                .then(function (response) {
                    setState(oldstate => {
                        let response_data = response.data
                        let paginated_results = {
                            ...oldstate,
                            next: response_data.next,
                            previous: response_data.previous,
                            count: response_data.count,
                            page_active: Number(response_data.page_active) + 1,
                            num_pages: response_data.num_pages,
                            data: response_data.data,
                            headers: [],
                            url: api_url,
                            limit: 5,
                            explore_type: "all"

                        };
                        return paginated_results
                    });

                })
                .catch(function (error) {
                    console.log(error)
                });

        } else {
            null
        }
    };

    const pageItem = () => {
        if (state && state.num_pages) {
            let pagi = state.num_pages.map(item => (
                <li key={item} className={`page-item ${state.page_active === item ?
                    'active' : ''}`}>
                    <div className="page-link">
                        {item}
                    </div>
                </li>
            ))
            return pagi
        } else {
            return null
        }

    }
    return (
        <>
            <nav aria-label="Page navigation example">
                <ul className="pagination">
                    <li className="page-item">
                        <div onClick={previousList} className="page-link page-link-arrow" aria-label="Previous">
                            <span aria-hidden="true">&laquo;</span>
                            <span className="sr-only">Previous</span>
                        </div>
                    </li>
                    {pageItem()}
                    <li className="page-item">
                        <div onClick={nextList} className="page-link page-link-arrow" aria-label="Next">
                            <span aria-hidden="true">&raquo;</span>
                            <span className="sr-only">Next</span>
                        </div>
                    </li>
                </ul>
            </nav>
        </>
    );
};

export default Pagination;
